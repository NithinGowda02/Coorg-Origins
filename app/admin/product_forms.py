from wtforms import BooleanField, DecimalField, FieldList, Form, FormField, HiddenField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class VariantForm(Form):
    id = HiddenField()
    label = StringField("Display label", validators=[DataRequired(), Length(max=80)])
    quantity_value = DecimalField("Quantity", validators=[DataRequired(), NumberRange(min=0)], places=3)
    quantity_unit = StringField("Unit", validators=[DataRequired(), Length(max=20)])
    price = DecimalField("Price", validators=[DataRequired(), NumberRange(min=0)], places=2)
    stock_quantity = IntegerField("Stock", validators=[DataRequired(), NumberRange(min=0)])
    sku = HiddenField()
    is_active = BooleanField("Active", default=True)


class ProductForm(FlaskForm):
    name = StringField("Product name", validators=[DataRequired(), Length(max=180)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    short_description = StringField("Short description", validators=[Optional(), Length(max=500)])
    description = TextAreaField("Description", validators=[Optional()])
    is_active = BooleanField("Active", default=True)
    is_featured = BooleanField("Featured product", default=False)
    images = MultipleFileField(
        "Product images",
        validators=[FileAllowed(["jpg", "jpeg", "png", "webp"], "Use JPG, PNG, or WebP images.")],
    )
    variants = FieldList(FormField(VariantForm), min_entries=1, max_entries=20)
    submit = SubmitField("Save product")
