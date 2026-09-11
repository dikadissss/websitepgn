"""The sections and items of the two paper checklists (September 2026). Credentials are not seeded: they are
entered in the admin (ChecklistItem.password, ChecklistSection.note), because this file is in the git repository."""
from django.db import migrations

EMAIL_WEB, DEVICE = 'email_web', 'device'

# (form, key, title, kind, note, [(name, address)])
SECTIONS = (
    (EMAIL_WEB, 'email', 'A. Cek Email (pengecekan email menggunakan Gmail berdasarkan username di bawah)', 'email',
     'Keterangan: J = Dijawab, BJ = Belum dijawab. Kelima email ini tergabung dalam 1 akun Gmail atas nama '
     'pgn@bmkg.go.id.\nPenting: jika ada peringatan dari PTWC/JMA (buletin 1 sampai dengan pengakhiran) yang '
     'berdampak ke Indonesia, segera forward.', [
         ('inartsp', 'inartsp@bmkg.go.id'),
         ('AEIC', 'aeic@bmkg.go.id'),
         ('monitrtwp', 'monitrtwp@bmkg.go.id'),
         ('info_inatews', 'info_inatews@bmkg.go.id'),
         ('Nscmcga', 'nscmcga@bmkg.go.id'),
     ]),
    (EMAIL_WEB, 'web-nasional', 'B. Cek Web dan Media Sosial untuk Gempabumi Dirasakan & Signifikan: Web Nasional',
     'web', 'Keterangan: B = Dibaca, BB = Belum dibaca.', [
         ('Web InaTEWS', 'http://inatews.bmkg.go.id'),
         ('Web RTSP Indonesia', 'http://rtsp.bmkg.go.id atau http://202.90.199.100'),
         ('Web Ina TnT', 'http://202.90.199.202/bmon/datastatus.php\nhttp://172.19.3.224:8080/'),
         ('Web BMKG', 'http://www.bmkg.go.id/gempabumi/gempabumi-dirasakan.bmkg'),
         ('Web BNPB', 'http://www.bnpb.go.id'),
         ('Instagram', 'https://www.instagram.com/infobmkg/'),
         ('Facebook', 'https://www.facebook.com/InfoBMKG'),
     ]),
    (EMAIL_WEB, 'web-internasional', 'Web Internasional', 'web', 'Keterangan: B = Dibaca, BB = Belum dibaca.', [
        ('USGS', 'http://earthquake.usgs.gov/earthquakes/map/'),
        ('Web PTWC', 'http://tsunami.gov'),
        ('Web JMA', 'https://www.data.jma.go.jp/multi/quake/index.html?lang=en'),
        ('Web Geofon', 'http://geofon.gfz-potsdam.de/eqinfo/list.php'),
        ('Web EMSC', 'http://www.emsc-csem.org/#2'),
        ('Web Global CMT', 'http://www.globalcmt.org/CMTsearch.html'),
        ('Web RTSP India', 'https://tsunami.incois.gov.in/TEWS/TSPindex.jsp'),
        ('Web RTSP Australia', 'http://www.bom.gov.au/tsunami/iotwms'),
        ('Web IOC-Tide Gauge', 'http://www.ioc-sealevelmonitoring.org/map.php'),
    ]),
    (DEVICE, 'sirine', 'Monitoring Sirine', 'check',
     'Catatan penting:\n1. Bila komputer hang, restart komputer.\n2. Apabila aplikasi sirine hang, tutup aplikasi lalu '
     'buka kembali dengan mengklik ikon Sirine Ina-TEWS di desktop. Bila masih hang, restart komputer sirine.', [
         ('Komputer sirine dalam keadaan siap (tidak hang)', ''),
         ('Aplikasi sirine dalam keadaan siap (tidak hang)', ''),
         ('Check list salah satu sirine, contoh pemda Padang: apakah sirine berubah dari merah menjadi kuning? '
          'Lakukan untuk pemda dan BMKG regional lainnya.', ''),
         ('Aplikasi Log Note sirine bisa diakses', 'http://192.168.1.1/bmkg/login/login.php'),
     ]),
    (DEVICE, 'seiscomp', 'Monitoring SeisComP (Meja D6, Client 2)', 'check', '', [
        ('Komputer SeisComP dalam keadaan siap (tidak hang)', ''),
        ('Feature SeisComP dapat digunakan (SCOLV, SCTTV, dll.)', ''),
        ('Apakah kondisi sinyal SeisComP masuk', ''),
    ]),
    (DEVICE, 'toast', 'Monitoring TOAST', 'check', '', [
        ('Komputer TOAST dalam keadaan siap (tidak hang)', ''),
        ('Apakah aplikasi TOAST dapat digunakan', ''),
    ]),
    (DEVICE, 'diseminasi', 'Monitoring Aplikasi Diseminasi', 'check', '', [
        ('Komputer Diseminasi dalam keadaan siap (tidak hang)', ''),
        ('Aplikasi Diseminasi telah ditutup', ''),
    ]),
    (DEVICE, 'tsp', 'Monitoring Aplikasi TSP', 'check', '', [
        ('Komputer TSP dalam keadaan siap (tidak hang)', ''),
        ('Aplikasi TSP telah ditutup', ''),
    ]),
    (DEVICE, 'wrs', 'Monitoring WRS', 'check', '', [
        ('Display aplikasi WRS NG dalam keadaan aktif', ''),
    ]),
)


def seed(apps, schema_editor):
    Section = apps.get_model('monitoring', 'ChecklistSection')
    Item = apps.get_model('monitoring', 'ChecklistItem')
    for order, (form, key, title, kind, note, items) in enumerate(SECTIONS, 1):
        section = Section.objects.create(form=form, key=key, title=title, kind=kind, order=order, note=note)
        Item.objects.bulk_create(Item(section=section, order=number, name=name, address=address)
                                 for number, (name, address) in enumerate(items, 1))


def unseed(apps, schema_editor):
    apps.get_model('monitoring', 'ChecklistSection').objects.filter(key__in=[key for _, key, *_ in SECTIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [('monitoring', '0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]
