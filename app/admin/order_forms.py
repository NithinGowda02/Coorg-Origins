from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField


ORDER_STATUSES = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("processing", "Processing"),
    ("shipped", "Shipped"),
    ("delivered", "Delivered"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]


class OrderStatusForm(FlaskForm):
    order_status = SelectField("Order status", choices=ORDER_STATUSES, validators=[])
    submit = SubmitField("Update status")
