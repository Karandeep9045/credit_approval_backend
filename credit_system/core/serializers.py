from rest_framework import serializers
from .models import Customer
import math

class CustomerRegisterSerializer(serializers.ModelSerializer):
    monthly_income = serializers.FloatField(write_only=True)  
    name = serializers.SerializerMethodField(read_only=True)  
    
    class Meta:
        model = Customer
        fields = ['customer_id', 'first_name', 'last_name', 'phone_number', 'monthly_income', 'age', 'name', 'approved_limit']
        read_only_fields = ['customer_id', 'name', 'approved_limit']
        extra_kwargs = {
            'first_name': {'write_only': True}, 
            'last_name': {'write_only': True},   
        }

    def get_name(self, obj):
        """Return combined first and last name"""
        return f"{obj.first_name} {obj.last_name}"

    def create(self, validated_data):
     
        last_customer = Customer.objects.order_by('customer_id').last()
        next_customer_id = (last_customer.customer_id + 1) if last_customer else 1
        
      
        monthly_income = validated_data.pop('monthly_income')
        validated_data['monthly_salary'] = monthly_income
        
      
        approved_limit = 36 * monthly_income
        approved_limit_rounded = round(approved_limit / 100000) * 100000 
        validated_data['approved_limit'] = approved_limit_rounded
        
      
        validated_data['customer_id'] = next_customer_id
        
        return Customer.objects.create(**validated_data)

    def to_representation(self, instance):
        """Custom response format"""
        return {
            'customer_id': instance.customer_id,
            'name': f"{instance.first_name} {instance.last_name}",
            'age': instance.age,
            'monthly_income': int(instance.monthly_salary),  
            'approved_limit': int(instance.approved_limit),
            'phone_number': instance.phone_number
        }


class LoanEligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=0)
    interest_rate = serializers.FloatField(min_value=0, max_value=50)
    tenure = serializers.IntegerField(min_value=1, max_value=50)


class LoanEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.FloatField()
    corrected_interest_rate = serializers.FloatField()
    tenure = serializers.IntegerField()
    monthly_installment = serializers.FloatField()


class CreateLoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.FloatField(min_value=0)
    interest_rate = serializers.FloatField(min_value=0, max_value=50)
    tenure = serializers.IntegerField(min_value=1, max_value=50)


class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.FloatField()


class CustomerDetailsSerializer(serializers.Serializer):
    """Customer details for loan view responses"""
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.IntegerField()
    age = serializers.IntegerField()


class ViewLoanResponseSerializer(serializers.Serializer):
    """Response for viewing a single loan details"""
    loan_id = serializers.IntegerField()
    customer = CustomerDetailsSerializer()
    loan_amount = serializers.FloatField() 
    interest_rate = serializers.FloatField()
    monthly_installment = serializers.FloatField()
    tenure = serializers.IntegerField()


class ViewLoansResponseSerializer(serializers.Serializer):
    """Response for viewing customer's loan list"""
    loan_id = serializers.IntegerField()
    loan_amount = serializers.FloatField()  
    interest_rate = serializers.FloatField()
    monthly_installment = serializers.FloatField()
    repayments_left = serializers.IntegerField()
