from django.db import models

from .choices import GROUP_CHOICES, Shift, local_today


class Operator(models.Model):
    """A duty officer (petugas). Also used as supervisor (SPV) and group member."""
    name = models.CharField(max_length=100)
    NIP = models.CharField(max_length=18)
    nickname = models.CharField(max_length=100, default='')

    class Meta:
        verbose_name = 'Petugas'
        verbose_name_plural = 'Petugas'
        ordering = ['name']

    def __str__(self):
        return self.name


class Kelompok(models.Model):
    name = models.IntegerField(choices=GROUP_CHOICES, default=1, unique=True)
    members = models.ManyToManyField(Operator, through='KelompokMember', blank=True)

    def __str__(self):
        return str(self.name)

    def ordered_members(self):
        """Members in the order they were arranged in the group form."""
        return [membership.operator for membership in self.memberships.select_related('operator')]

    def set_members(self, operator_ids):
        self.memberships.all().delete()
        KelompokMember.objects.bulk_create(
            KelompokMember(kelompok=self, operator_id=operator_id)
            for operator_id in dict.fromkeys(operator_ids)
        )


class KelompokMember(models.Model):
    kelompok = models.ForeignKey(Kelompok, on_delete=models.CASCADE, related_name='memberships')
    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name='memberships')

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['kelompok', 'operator'], name='unique_kelompok_member'),
        ]


class DutyRecord(models.Model):
    """Fields shared by every job done during a duty (dinas): when, by which group and by whom."""
    code_field = None  # Name of the record's business id field, e.g. 'qc_id'.

    date = models.DateField(default=local_today)
    shift = models.CharField(max_length=15, choices=Shift.choices, default=Shift.PAGI)
    kelompok = models.PositiveSmallIntegerField(choices=GROUP_CHOICES, default=1, db_index=True)
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT)

    class Meta:
        abstract = True
        indexes = [models.Index(fields=['date', 'shift', 'kelompok'], name='%(app_label)s_%(class)s_slot')]

    def __str__(self):
        return getattr(self, self.code_field)

    @property
    def code(self):
        return getattr(self, self.code_field)
