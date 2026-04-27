import polib

po_ru = polib.pofile('locale/ru/LC_MESSAGES/django.po')

trans_map = {
    "Uy xizmatlari eshigingizgacha": "Домашние услуги до вашей двери",
    "Nima qidiryapsiz?": "Что вы ищете?",
    "Chuqur tozalash<br>va dezinfeksiya": "Глубокая уборка<br>и дезинфекция",
    "Uy ta'miri<br>va maishiy ish": "Ремонт дома<br>и бытовые работы",
    "Mebel yig'ish": "Сборка мебели",
    "Santexnik kerak": "Нужен сантехник",
    "Rozetka o'rnatish": "Установка розетки",
    "Chuqur tozalash": "Глубокая уборка",
    "Split-sistema": "Сплит-система",
    "Devor bo'yash": "Покраска стен",
    "Kran almashtirish": "Замена крана",
    "Lyustra o'rnatish": "Установка люстры",
    "Oyna tozalash": "Мытье окон",
    "Konditsioner servis": "Обслуживание кондиционера",
    "Plitka yotqizish": "Укладка плитки",
    "Bolier ta'mir": "Ремонт бойлера",
    "Sim o'tkazish": "Проводка",
    "Umumiy tozalash": "Генеральная уборка",
    "Shift ta'miri": "Ремонт потолка",
    "Freon to'ldirish": "Заправка фреоном",
    "Unitaz o'rnatish": "Установка унитаза",
    "Shit yig'ish": "Сборка щитка",
    "Xona tozalash": "Уборка комнаты",
    "Gipskarton shift": "Потолок из гипсокартона",
    "Klimat o'rnatish": "Установка климата",
    "Chilonzor": "Чиланзар",
    "Yunusobod": "Юнусабад",
    "Mirzo Ulug'bek": "Мирзо-Улугбек",
    "Yakkasaroy": "Яккасарай",
    "Shayxontohur": "Шайхантахур",
    "Olmazor": "Олмазар",
    "Mirobod": "Мирабад",
    "Yashnobod": "Яшнабад",
    "Uchtepa": "Учтепа",
    "Chorsu": "Чорсу",
    "Amir Temur": "Амир Темур",
    "TTZ": "ТТЗ",
    "Yangihayot": "Янгихаёт",
    "Beruniy": "Беруни",
    "Hadra": "Хадра",
    "Oybek": "Ойбек",
    "Paxtakor": "Пахтакор",
    "Mustaqillik": "Мустакиллик",
    "Darxon": "Дархан",
    "Pushkin": "Пушкин",
    "Uy <span class=\"accent-word\">xizmatlari</span><br>eshigingizgacha": "Домашние <span class=\"accent-word\">услуги</span><br>до вашей двери",
    "Siz ham usta bo'ling\nva 15 mln so'mgacha toping": "Станьте мастером и зарабатывайте до 15 млн сум",
    "Shahar bo'ylab joriy interaktiv xaritani bevosita kuzating.": "Отслеживайте текущую интерактивную карту по всему городу."
}

for entry in po_ru:
    msg = entry.msgid.replace("\\'", "'")
    if msg in trans_map:
        entry.msgstr = trans_map[msg]
    elif entry.msgid in trans_map:
        entry.msgstr = trans_map[entry.msgid]

po_ru.save()
print("RU translations saved successfully.")
