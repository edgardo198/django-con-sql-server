from django.forms import CharField, Form, TextInput


class ReportForm(Form):
    date_range = CharField(widget=TextInput(attrs={
        'class': 'form-control',
        'autocomplete': 'off',
        'placeholder': 'Seleccione un rango de fechas',
    }))
