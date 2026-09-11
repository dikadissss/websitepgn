"""The catalog of the 2026 templates (Checklist Email_2026.xlsx, Checklist Sirine_2026.xlsx): section headings and
notes with the admins' contacts, the new Ina TnT address, and no Sirine section any more (its saved answers go too).
Passwords are still entered in the admin only."""
from django.db import migrations, models

SECTIONS = {
    'email': {
        'heading': 'A. CEK EMAIL (Saat ini pengecekan email menggunakan GMAIL berdasarkan nama dari username dibawah)',
        'title': 'Cek Email',
        'side_note': 'Kelima email ini tergabung dalam 1 akun gmail atas nama email "pgn@bmkg.go.id"',
        'note': 'Keterangan :  J   = Dijawab\n                       BJ = Belum dijawab\n'
                'Admin Email BMKG = Akbar (087777888821, email: akbar@bmkg.go.id)',
        'note_right': 'Penting : Jika ada peringatan dari PTWC/JMA (buletin 1 sampai dengan pengakhiran) yang berdampak '
                      'ke Indonesia, maka segera forward ke :\nbayu.pranata@bmkg.go.id\npgn@bmkg.go.id',
    },
    'web-nasional': {
        'heading': 'B. CEK WEB DAN MEDIA SOSIAL UNTUK GEMPABUMI DIRASAKAN & SIGNIFIKAN',
        'title': 'Web Nasional',
        'side_note': '',
        'note': 'Keterangan :  B   = Dibaca\n                       BB = Belum dibaca',
        'note_right': 'Admin Web BMKG = Akbar (087777888821, email: akbar@bmkg.go.id)\n'
                      'Admin Web BNPB = Leonard (08568894099)\n'
                      'Admin Web InaTEWS, Web RTSP Indonesia = Karyono (081311001511, email: karyonosu@gmail.com)\n'
                      '                                                                     = Yedi (085221220808, '
                      'email: ydermadi@yahoo.com)',
    },
    'web-internasional': {
        'heading': '',
        'title': 'Web Internasional',
        'side_note': '',
        'note': 'Keterangan :  B   = Dibaca\n                       BB = Belum dibaca',
        'note_right': 'Nomor Kontak Jaringan = Ekstension : 1500\n'
                      '                                     = Dudi (08569908578)',
    },
    'seiscomp': {'title': 'MONITORING SeisComP (Meja D6, Client 2)'},
    'toast': {'title': 'MONITORING TOAST'},
    'diseminasi': {'title': 'MONITORING Aplikasi Diseminasi'},
    'tsp': {'title': 'MONITORING Aplikasi TSP'},
    'wrs': {'title': 'MONITORING WRS'},
}


def update(apps, schema_editor):
    Section = apps.get_model('monitoring', 'ChecklistSection')
    Item = apps.get_model('monitoring', 'ChecklistItem')
    Section.objects.filter(key='sirine').delete()
    apps.get_model('monitoring', 'DeviceAnswer').objects.filter(section_key='sirine').delete()
    for key, values in SECTIONS.items():
        Section.objects.filter(key=key).update(**values)
        # Saved answers keep their section title: rename it too, so an old record does not print the new heading
        # above a title that already holds it ("B. Cek Web ...: Web Nasional").
        for model in ('EmailWebAnswer', 'DeviceAnswer'):
            apps.get_model('monitoring', model).objects.filter(section_key=key).update(section_title=values['title'])
    Item.objects.filter(section__key='email', name='inartsp').update(name='Inartsp')
    Item.objects.filter(section__key='web-nasional', name='Web Ina TnT').update(
        address='http://202.90.199.202/tntmon/datastatus.php\nhttp://172.19.3.224:8080/')


class Migration(migrations.Migration):
    dependencies = [('monitoring', '0002_seed_items')]
    operations = [
        migrations.AddField(
            model_name='checklistsection',
            name='heading',
            field=models.CharField(blank=True, help_text='Judul bagian dicetak di atas tabel, misalnya "A. CEK EMAIL (...)".', max_length=200),
        ),
        migrations.AddField(
            model_name='checklistsection',
            name='side_note',
            field=models.TextField(blank=True, help_text='Tabel email: dicetak di kolom samping, sepanjang semua baris.'),
        ),
        migrations.AddField(
            model_name='checklistsection',
            name='note_right',
            field=models.TextField(blank=True, help_text='Dicetak di kanan bawah tabel, misalnya kontak admin.'),
        ),
        migrations.AlterField(
            model_name='checklistsection',
            name='note',
            field=models.TextField(blank=True, help_text='Dicetak di kiri bawah tabel, misalnya keterangan J/BJ.'),
        ),
        migrations.AlterField(
            model_name='checklistsection',
            name='form',
            field=models.CharField(choices=[('email_web', 'Monitoring Email, Web, Medsos dan WRS-NG'), ('device', 'Checklist SeisComP (Backup), TOAST, Diseminasi, TSP dan WRS NG')], max_length=20),
        ),
        migrations.RunPython(update, migrations.RunPython.noop),
    ]
