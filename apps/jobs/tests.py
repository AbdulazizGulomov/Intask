from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.jobs.models import Job


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
