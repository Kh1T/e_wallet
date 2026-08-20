# Data migration for Cambodia Administrative Divisions
# Includes all 25 provinces and sample data for districts, communes, and villages

from django.db import migrations


def load_cambodia_geography(apps, schema_editor):
    """Load Cambodia provinces, districts, communes and sample villages."""
    Province = apps.get_model('wallet', 'Province')
    District = apps.get_model('wallet', 'District')
    Commune = apps.get_model('wallet', 'Commune')
    Village = apps.get_model('wallet', 'Village')

    # Cambodia 25 Provinces
    provinces_data = [
        ('01', 'ភ្នំពេញ', 'Phnom Penh'),
        ('02', 'បាត់ដំបង', 'Battambang'),
        ('03', 'កំពង់ចាម', 'Kampong Cham'),
        ('04', 'កំពង់ឆ្នាំង', 'Kampong Chhnang'),
        ('05', 'កំពង់ស្ពឺ', 'Kampong Speu'),
        ('06', 'កំពង់ធំ', 'Kampong Thom'),
        ('07', 'កំពត', 'Kampot'),
        ('08', 'កណ្តាល', 'Kandal'),
        ('09', 'កោះកុង', 'Koh Kong'),
        ('10', 'ក្រចេះ', 'Kratie'),
        ('11', 'មណ្ឌលគិរី', 'Mondulkiri'),
        ('12', 'ព្រះវិហារ', 'Preah Vihear'),
        ('13', 'ព្រះសីហនុ', 'Preah Sihanouk'),
        ('14', 'ពោធិ៍សាត់', 'Pursat'),
        ('15', 'រតនគិរី', 'Ratanakiri'),
        ('16', 'សៀមរាប', 'Siem Reap'),
        ('17', 'ស្ទឹងត្រែង', 'Stung Treng'),
        ('18', 'ស្វាយរៀង', 'Svay Rieng'),
        ('19', 'តាកែវ', 'Takeo'),
        ('20', 'ឧត្តរមានជ័យ', 'Oddar Meanchey'),
        ('21', 'កែប', 'Kep'),
        ('22', 'ប៉ៃលិន', 'Pailin'),
        ('23', 'ត្បូងឃ្មុំ', 'Tboung Khmum'),
        ('24', 'បន្ទាយមានជ័យ', 'Banteay Meanchey'),
    ]

    for code, name, name_en in provinces_data:
        Province.objects.get_or_create(
            code=code,
            defaults={'name': name, 'name_other': name_en, 'is_active': True}
        )

    # Sample Districts for major provinces (Khan/Srok)
    # Phnom Penh Districts (Khan)
    phnom_penh = Province.objects.get(code='01')
    pp_districts = [
        ('0101', 'ចំការមន', 'Chamkar Mon'),
        ('0102', 'ដូនពេញ', 'Daun Penh'),
        ('0103', '៧មករា', 'Prampi Makara'),
        ('0104', 'ទួលគោក', 'Tuol Kork'),
        ('0105', 'សែនសុខ', 'Sen Sok'),
        ('0106', 'ពោធិ៍សែនជ័យ', 'Por Senchey'),
        ('0107', 'ឬស្សីកែវ', 'Russey Keo'),
        ('0108', 'ច្បារអំពៅ', 'Chbar Ampov'),
        ('0109', 'ព្រែកព្នៅ', 'Prek Pnov'),
        ('0110', 'ដង្កោ', 'Dangkao'),
        ('0111', 'ជ្រោយចង្វា', 'Chroy Changvar'),
        ('0112', 'ព្រែកលាប', 'Prek Lieab'),
        ('0113', 'ព្រៃស', 'Praek Sa'),
        ('0114', 'បឹងខែម', 'Boeng Keng Kang'),
    ]
    for code, name, name_en in pp_districts:
        District.objects.get_or_create(
            code=code,
            defaults={'province': phnom_penh, 'name': name, 'name_other': name_en, 'is_active': True}
        )

    # Siem Reap Districts (Srok)
    siem_reap = Province.objects.get(code='16')
    sr_districts = [
        ('1601', 'ស្រុកអង្គរជ័យ', 'Angkor Chey'),
        ('1602', 'ស្រុកបាស្តៈ', 'Basedth'),
        ('1603', 'ស្រុកច្បារអំពៅ', 'Chbar Ampov'),
        ('1604', 'ស្រុកជីក្រែង', 'Chi Kraeng'),
        ('1605', 'ក្រុងសៀមរាប', 'Siem Reap City'),
        ('1606', 'ស្រុកកណ្តៀល', 'Kandaek'),
        ('1607', 'ស្រុកកំពង់ឃ្លាំង', 'Kampong Khleang'),
        ('1608', 'ស្រុកពួក', 'Puok'),
        ('1609', 'ស្រុកប្រាសាទបាគង', 'Prasat Bakong'),
    ]
    for code, name, name_en in sr_districts:
        District.objects.get_or_create(
            code=code,
            defaults={'province': siem_reap, 'name': name, 'name_other': name_en, 'is_active': True}
        )

    # Sample Communes (Khum) for Siem Reap City
    sr_city = District.objects.get(code='1605')
    sr_communes = [
        ('160501', 'សង្កាត់ស្វាយចន្ទ', 'Svay Dangkum'),
        ('160502', 'សង្កាត់វត្តបក់', 'Wat Bo'),
        ('160503', 'សង្កាត់សាលាកំរើក', 'Sala Kamreuk'),
        ('160504', 'សង្កាត់គោកចក', 'Kokchak'),
        ('160505', 'សង្កាត់ជ័យ', 'Chey'),
        ('160506', 'សង្កាត់ស្លរក្សារម៉ាស់', 'Slor Kram'),
        ('160507', 'សង្កាត់អណ្តូងព្រិច', 'Andoung Phleuk'),
        ('160508', 'សង្កាត់តាភេម', 'Ta Phul'),
        ('160509', 'សង្កាត់គំរប់', 'Krom'),
        ('160510', 'សង្កាត់ចុងឃ្លាំង', 'Chong Khneas'),
    ]
    for code, name, name_en in sr_communes:
        Commune.objects.get_or_create(
            code=code,
            defaults={'district': sr_city, 'name': name, 'name_other': name_en, 'is_active': True}
        )

    # Sample Villages (Phum) for Svay Dangkum commune
    svay_dangkum = Commune.objects.get(code='160501')
    villages = [
        ('16050101', 'ភូមិវត្តបក់', 'Wat Bo'),
        ('16050102', 'ភូមិស្លែងខាងជើង', 'Slaeng Khang Cheung'),
        ('16050103', 'ភូមិស្លែងខាងត្បូង', 'Slaeng Khang Tboung'),
        ('16050104', 'ភូមិចំការស្រូវ', 'Chamkar Sraov'),
        ('16050105', 'ភូមិគោកត្បែង', 'Kok Thlaeung'),
        ('16050106', 'ភូមិត្រពាំងធំ', 'Trapang Thum'),
        ('16050107', 'ភូមិព្រៃទួល', 'Prey Tuol'),
        ('16050108', 'ភូមិស្វាយចន្ទ', 'Svay Dangkum'),
    ]
    for code, name, name_en in villages:
        Village.objects.get_or_create(
            code=code,
            defaults={'commune': svay_dangkum, 'name': name, 'name_other': name_en, 'is_active': True}
        )

    # Sample Communes for Chamkar Mon (Phnom Penh)
    chamkar_mon = District.objects.get(code='0101')
    cm_communes = [
        ('010101', 'សង្កាត់ទន្លេបាសាក់', 'Tonle Basak'),
        ('010102', 'សង្កាត់ទំនប់រ៉ូហ្សេ', 'Tumnob Rolok'),
        ('010103', 'សង្កាត់បឹងត្របែក', 'Boeng Trabek'),
        ('010104', 'សង្កាត់ផ្សារដើមថ្កូវ', 'Phsar Daeum Thkov'),
        ('010105', 'សង្កាត់ទួលទំពូងទី១', 'Tuol Tumpung 1'),
        ('010106', 'សង្កាត់ទួលទំពូងទី២', 'Tuol Tumpung 2'),
        ('010107', 'សង្កាត់បឹងកេងកងទី១', 'Boeng Keng Kang 1'),
        ('010108', 'សង្កាត់បឹងកេងកងទី២', 'Boeng Keng Kang 2'),
        ('010109', 'សង្កាត់បឹងកេងកងទី៣', 'Boeng Keng Kang 3'),
        ('010110', 'សង្កាត់អូឡាំពិក', 'Olympic'),
    ]
    for code, name, name_en in cm_communes:
        Commune.objects.get_or_create(
            code=code,
            defaults={'district': chamkar_mon, 'name': name, 'name_other': name_en, 'is_active': True}
        )

    # Sample Villages for Tonle Basak
    tonle_basak = Commune.objects.get(code='010101')
    tb_villages = [
        ('01010101', 'ភូមិ១', 'Village 1'),
        ('01010102', 'ភូមិ២', 'Village 2'),
        ('01010103', 'ភូមិ៣', 'Village 3'),
        ('01010104', 'ភូមិ៤', 'Village 4'),
        ('01010105', 'ភូមិ៥', 'Village 5'),
        ('01010106', 'ភូមិ៦', 'Village 6'),
        ('01010107', 'ភូមិ៧', 'Village 7'),
        ('01010108', 'ភូមិ៨', 'Village 8'),
        ('01010109', 'ភូមិ៩', 'Village 9'),
        ('01010110', 'ភូមិ១០', 'Village 10'),
    ]
    for code, name, name_en in tb_villages:
        Village.objects.get_or_create(
            code=code,
            defaults={'commune': tonle_basak, 'name': name, 'name_other': name_en, 'is_active': True}
        )


def reverse_geography(apps, schema_editor):
    """Reverse the data migration."""
    Province = apps.get_model('wallet', 'Province')
    Province.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0012_address_hierarchy_models'),
    ]

    operations = [
        migrations.RunPython(load_cambodia_geography, reverse_geography),
    ]
