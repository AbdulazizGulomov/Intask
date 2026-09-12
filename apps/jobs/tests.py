from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import WorkerProfile
from apps.jobs.models import Job, JobApplication, Profession
from apps.jobs.utils import haversine_km
from apps.orders.models import Order


def _yandex_response(components, formatted):
    """Minimal Yandex Geocoder 1.x reverse-geocode JSON body."""
    return {
        "response": {
            "GeoObjectCollection": {
                "featureMember": [
                    {
                        "GeoObject": {
                            "metaDataProperty": {
                                "GeocoderMetaData": {
                                    "Address": {
                                        "formatted": formatted,
                                        "Components": components,
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        }
    }


class ReverseGeocodeAPITests(TestCase):
    URL = "/api/geocode/reverse/"

    def setUp(self):
        cache.clear()  # geocode results and throttle counters both live here

    def _mock_get(self, components, formatted):
        resp = mock.Mock(status_code=200)
        resp.json.return_value = _yandex_response(components, formatted)
        return mock.patch("apps.jobs.geocode.requests.get", return_value=resp)

    def test_city_district(self):
        components = [
            {"kind": "country", "name": "O‘zbekiston"},
            {"kind": "province", "name": "O‘zbekiston"},
            {"kind": "province", "name": "Toshkent Shahri"},
            {"kind": "locality", "name": "Toshkent"},
            {"kind": "district", "name": "Yunusobod tumani"},
            {"kind": "street", "name": "Amir Temur ko‘chasi"},
            {"kind": "house", "name": "12"},
        ]
        with mock.patch("apps.jobs.geocode._geocoder_api_key", return_value="k"), \
                self._mock_get(components, "Toshkent, Amir Temur ko‘chasi, 12") as m:
            r = self.client.get(self.URL, {"lat": "41.3110", "lng": "69.2790", "lang": "uz"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["region"], "toshkent_city")
        self.assertEqual(data["district"], "Yunusobod tumani")
        self.assertEqual(data["street"], "Amir Temur ko‘chasi")
        self.assertEqual(data["house"], "12")
        self.assertEqual(data["formatted"], "Toshkent, Amir Temur ko‘chasi, 12")
        self.assertNotIn("error", data)
        # lang mapping uz → uz_UZ reaches the upstream call
        self.assertEqual(m.call_args.kwargs["params"]["lang"], "uz_UZ")

    def test_rural_area_and_russian_province(self):
        components = [
            {"kind": "country", "name": "Узбекистан"},
            {"kind": "province", "name": "Узбекистан"},
            {"kind": "province", "name": "Ташкентская область"},
            {"kind": "area", "name": "Зангиатинский район"},
            {"kind": "locality", "name": "Эшангузар"},
        ]
        with mock.patch("apps.jobs.geocode._geocoder_api_key", return_value="k"), \
                self._mock_get(components, "Ташкентская область, Зангиатинский район"):
            r = self.client.get(self.URL, {"lat": "41.20", "lng": "69.10", "lang": "ru"})
        data = r.json()
        self.assertEqual(data["region"], "toshkent")
        # No city district → rural area (tuman) wins over locality.
        self.assertEqual(data["district"], "Зангиатинский район")
        self.assertEqual(data["street"], "")
        self.assertEqual(data["house"], "")

    def test_no_api_key_still_200(self):
        with mock.patch("apps.jobs.geocode._geocoder_api_key", return_value=""):
            r = self.client.get(self.URL, {"lat": "41.311", "lng": "69.279"})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["error"], "no_api_key")
        for field in ("region", "district", "street", "house", "formatted"):
            self.assertEqual(data[field], "")

    def test_invalid_coords_400(self):
        for params in ({"lat": "abc", "lng": "69"}, {"lat": "91", "lng": "69"}, {"lng": "69"}):
            self.assertEqual(self.client.get(self.URL, params).status_code, 400)


class JobCreateAPITests(TestCase):
    URL = "/api/jobs/create/"

    def setUp(self):
        self.user = get_user_model().objects.create(phone="+998901112233", role="employer")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _payload(self, **extra):
        base = {
            "title": "Usta kerak",
            "region": "toshkent_city",
            "job_type": "daily",
            "district": "Yunusobod tumani",
            "street": "Amir Temur ko‘chasi",
            "house": "12",
            "landmark": "Metro yonida",
        }
        base.update(extra)
        return base

    def test_create_with_address_parts_derives_address(self):
        r = self.client.post(self.URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        job = Job.objects.get(id=r.json()["id"])
        self.assertEqual(job.district, "Yunusobod tumani")
        self.assertEqual(job.street, "Amir Temur ko‘chasi")
        self.assertEqual(job.house, "12")
        self.assertEqual(job.landmark, "Metro yonida")
        # address derived from street + house; landmark deliberately excluded
        self.assertEqual(job.address, "Amir Temur ko‘chasi, 12")
        # and the four fields round-trip through the response serializer
        data = r.json()
        for field in ("district", "street", "house", "landmark"):
            self.assertEqual(data[field], getattr(job, field))

    def test_explicit_address_wins(self):
        r = self.client.post(self.URL, self._payload(address="Chilonzor 19"), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Job.objects.get(id=r.json()["id"]).address, "Chilonzor 19")

    def test_house_only_no_dangling_comma(self):
        r = self.client.post(self.URL, self._payload(street="", house="12"), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Job.objects.get(id=r.json()["id"]).address, "12")

    def test_fields_in_public_list(self):
        self.client.post(self.URL, self._payload(), format="json")
        r = APIClient().get("/api/jobs/")
        self.assertEqual(r.status_code, 200)
        item = r.json()["results"][0]
        self.assertEqual(item["district"], "Yunusobod tumani")
        self.assertEqual(item["landmark"], "Metro yonida")

    def test_workers_needed_defaults_to_one_and_accepts_a_value(self):
        r = self.client.post(self.URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["workers_needed"], 1)
        self.assertEqual(Job.objects.get(id=r.json()["id"]).workers_needed, 1)

        r = self.client.post(self.URL, self._payload(workers_needed="3"), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["workers_needed"], 3)

    def test_workers_needed_must_be_a_positive_integer(self):
        for bad in ("0", "-2", "abc", "1.5"):
            r = self.client.post(self.URL, self._payload(workers_needed=bad), format="json")
            self.assertEqual(r.status_code, 400, bad)
            self.assertIn("workers_needed", r.json())


class HaversineTests(TestCase):
    def test_zero_for_identical_points(self):
        self.assertEqual(haversine_km(41.31, 69.28, 41.31, 69.28), 0)

    def test_one_degree_of_latitude_is_about_111_km(self):
        d = haversine_km(41, 69, 42, 69)
        self.assertGreater(d, 110)
        self.assertLess(d, 112)

    def test_none_when_a_coordinate_is_missing_or_invalid(self):
        self.assertIsNone(haversine_km(None, 69, 41, 69))
        self.assertIsNone(haversine_km(41, 69, 41, None))
        self.assertIsNone(haversine_km("x", 69, 41, 69))

    def test_numeric_strings_are_accepted(self):
        self.assertAlmostEqual(haversine_km("41.31", "69.28", "41.32", "69.28"), 1.11, delta=0.05)


class EmployerApplicationsAPITests(TestCase):
    """GET /api/jobs/<id>/applications/ and the accept / reject decisions."""

    def setUp(self):
        User = get_user_model()
        self.employer = User.objects.create(phone="+998900000010", role="employer")
        self.other_employer = User.objects.create(phone="+998900000011", role="employer")
        self.profession = Profession.objects.create(name="Yuk tashuvchi", name_ru="Грузчик")
        self.job = Job.objects.create(
            employer=self.employer, title="Omborga yuk tashuvchi", region="toshkent_city",
            job_type="daily", lat=41.311, lng=69.280, workers_needed=2,
        )
        self.other_job = Job.objects.create(
            employer=self.other_employer, title="Boshqa ish", region="toshkent_city", job_type="daily",
        )

        # w1: full profile, ~1 km north of the job, two rated completed orders
        self.w1 = User.objects.create(phone="+998900000021", role="worker")
        WorkerProfile.objects.create(
            user=self.w1, first_name="Bekzod", last_name="Rasulov", age=28,
            profession=self.profession, lat=41.320, lng=69.280,
        )
        # w2: profile without coords / profession / age
        self.w2 = User.objects.create(phone="+998900000022", role="worker")
        WorkerProfile.objects.create(user=self.w2, first_name="Sardor", last_name="Aliyev")
        # w3: no profile at all
        self.w3 = User.objects.create(phone="+998900000023", role="worker")

        now = timezone.now()
        self.a1 = JobApplication.objects.create(job=self.job, worker=self.w1, employer=self.employer)
        self.a2 = JobApplication.objects.create(
            job=self.job, worker=self.w2, employer=self.employer, status=JobApplication.Status.ACCEPTED,
        )
        self.a3 = JobApplication.objects.create(job=self.job, worker=self.w3, employer=self.employer)
        # auto_now_add gives near-identical stamps; pin them so the order is testable
        JobApplication.objects.filter(pk=self.a1.pk).update(created_at=now - timedelta(hours=2))
        JobApplication.objects.filter(pk=self.a2.pk).update(created_at=now - timedelta(hours=1))
        JobApplication.objects.filter(pk=self.a3.pk).update(created_at=now)
        self.foreign = JobApplication.objects.create(
            job=self.other_job, worker=self.w1, employer=self.other_employer,
        )

        for title, st, rating in (("a", Order.Status.COMPLETED, 5), ("b", Order.Status.COMPLETED, 4),
                                  ("c", Order.Status.CANCELLED, None)):
            Order.objects.create(
                employer=self.employer, worker=self.w1, title=title, status=st, employer_rating=rating,
            )

        self.client = APIClient()
        self.client.force_authenticate(self.employer)

    def _url(self, job=None):
        return f"/api/jobs/{(job or self.job).id}/applications/"

    def test_list_requires_the_owner(self):
        self.assertEqual(APIClient().get(self._url()).status_code, 401)
        for user in (self.other_employer, self.w1):
            c = APIClient()
            c.force_authenticate(user)
            self.assertEqual(c.get(self._url()).status_code, 403, user)
        self.assertEqual(self.client.get("/api/jobs/999999/applications/").status_code, 404)

    def test_list_shape_newest_first(self):
        r = self.client.get(self._url())
        self.assertEqual(r.status_code, 200, r.content)
        rows = r.json()
        self.assertEqual([x["id"] for x in rows], [self.a3.id, self.a2.id, self.a1.id])
        self.assertEqual([x["status"] for x in rows], ["pending", "accepted", "pending"])
        for x in rows:
            self.assertEqual(
                set(x), {"id", "status", "created_at", "worker"},
            )
            self.assertEqual(
                set(x["worker"]),
                {"id", "first_name", "last_name", "phone", "professions", "rating",
                 "jobs_done", "age", "distance_km"},
            )

        bekzod = rows[2]["worker"]
        self.assertEqual(bekzod["id"], self.w1.id)
        self.assertEqual(bekzod["first_name"], "Bekzod")
        self.assertEqual(bekzod["last_name"], "Rasulov")
        self.assertEqual(bekzod["phone"], "+998900000021")
        self.assertEqual(bekzod["professions"], ["Yuk tashuvchi"])
        self.assertEqual(bekzod["rating"], 4.5)   # (5 + 4) / 2, cancelled order ignored
        self.assertEqual(bekzod["jobs_done"], 2)  # completed only
        self.assertEqual(bekzod["age"], 28)
        self.assertAlmostEqual(bekzod["distance_km"], 1.0, delta=0.2)

        sardor = rows[1]["worker"]
        self.assertEqual(sardor["professions"], [])
        self.assertIsNone(sardor["rating"])
        self.assertEqual(sardor["jobs_done"], 0)
        self.assertIsNone(sardor["age"])
        self.assertIsNone(sardor["distance_km"])  # no worker coords

        no_profile = rows[0]["worker"]
        self.assertEqual(no_profile["first_name"], "")
        self.assertEqual(no_profile["phone"], "+998900000023")
        self.assertIsNone(no_profile["distance_km"])

    def test_distance_is_null_when_the_job_has_no_coords(self):
        Job.objects.filter(pk=self.job.pk).update(lat=None, lng=None)
        rows = self.client.get(self._url()).json()
        self.assertTrue(all(x["worker"]["distance_km"] is None for x in rows))

    def test_accept_then_conflict(self):
        r = self.client.post(f"/api/applications/{self.a1.id}/accept/")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data["id"], self.a1.id)
        self.assertEqual(data["status"], "accepted")
        self.assertEqual(data["worker"]["first_name"], "Bekzod")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.status, JobApplication.Status.ACCEPTED)

        # not pending any more -> 409, for either decision
        self.assertEqual(self.client.post(f"/api/applications/{self.a1.id}/accept/").status_code, 409)
        r = self.client.post(f"/api/applications/{self.a1.id}/reject/")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["status"], "accepted")
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.status, JobApplication.Status.ACCEPTED)

    def test_reject(self):
        r = self.client.post(f"/api/applications/{self.a3.id}/reject/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["status"], "rejected")
        self.a3.refresh_from_db()
        self.assertEqual(self.a3.status, JobApplication.Status.REJECTED)
        # already-accepted rows cannot be flipped either
        self.assertEqual(self.client.post(f"/api/applications/{self.a2.id}/reject/").status_code, 409)

    def test_decisions_require_the_owner(self):
        for path in (f"/api/applications/{self.a1.id}/accept/", f"/api/applications/{self.a1.id}/reject/"):
            self.assertEqual(APIClient().post(path).status_code, 401)
            for user in (self.other_employer, self.w1):
                c = APIClient()
                c.force_authenticate(user)
                self.assertEqual(c.post(path).status_code, 403, (path, user))
        # the owner of a different job cannot touch this one's applications
        self.assertEqual(self.client.post(f"/api/applications/{self.foreign.id}/accept/").status_code, 403)
        self.assertEqual(self.client.post("/api/applications/999999/accept/").status_code, 404)
        self.a1.refresh_from_db()
        self.assertEqual(self.a1.status, JobApplication.Status.PENDING)

    def test_job_detail_exposes_workers_needed_and_accepted_count(self):
        r = APIClient().get(f"/api/jobs/{self.job.id}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["workers_needed"], 2)
        self.assertEqual(r.json()["accepted_count"], 1)
        self.client.post(f"/api/applications/{self.a1.id}/accept/")
        self.assertEqual(APIClient().get(f"/api/jobs/{self.job.id}/").json()["accepted_count"], 2)

        item = next(x for x in APIClient().get("/api/jobs/").json()["results"] if x["id"] == self.job.id)
        self.assertEqual(item["workers_needed"], 2)
        self.assertNotIn("accepted_count", item)  # detail-only

    def test_worker_side_endpoints_unchanged(self):
        c = APIClient()
        c.force_authenticate(self.w1)
        mine = c.get("/api/my-applications/").json()
        self.assertEqual({x["status"] for x in mine}, {"pending"})
        self.assertEqual(set(mine[0]), {"id", "status", "applied_at", "job"})
