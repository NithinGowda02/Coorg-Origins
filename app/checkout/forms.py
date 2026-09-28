from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class CheckoutForm(FlaskForm):
    customer_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    phone = StringField("Phone", validators=[DataRequired(), Length(min=7, max=30)])
    address_line = StringField("Address", validators=[DataRequired(), Length(max=255)])
    city = StringField("City", validators=[DataRequired(), Length(max=100)])
    state = StringField("State", validators=[DataRequired(), Length(max=100)])
    postal_code = StringField("PIN code", validators=[DataRequired(), Length(min=4, max=20)])
    submit = SubmitField("Create order")


class PaymentForm(FlaskForm):
    transaction_reference = StringField("UPI transaction reference", validators=[DataRequired(), Length(max=120)])
    submit = SubmitField("Submit for verification")
