from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    CustomerRegisterSerializer, 
    LoanEligibilityRequestSerializer, 
    LoanEligibilityResponseSerializer,
    CreateLoanRequestSerializer,
    CreateLoanResponseSerializer,
    ViewLoanResponseSerializer,
    ViewLoansResponseSerializer
)
from .models import Customer, Loan
from django.db.models import Sum, Q, Count
from datetime import datetime, date
import math
from django.http import HttpResponse


from django.http import HttpResponse

from django.http import HttpResponse
from django.shortcuts import render

def home(request):
    return render(request, 'home.html')



class RegisterCustomerView(APIView):
    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save()
           
            return Response(serializer.to_representation(customer), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoanEligibilityView(APIView):
    def post(self, request):
        request_serializer = LoanEligibilityRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = request_serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        credit_score = self.calculate_credit_score(customer)
        approval, corrected_interest_rate = self.check_loan_approval(customer, credit_score, loan_amount, interest_rate, tenure)
        
        monthly_installment = self.calculate_monthly_installment(
            loan_amount, corrected_interest_rate, tenure
        ) if approval else 0

        response_data = {
            'customer_id': customer_id,
            'approval': approval,
            'interest_rate': interest_rate,
            'corrected_interest_rate': corrected_interest_rate,
            'tenure': tenure,
            'monthly_installment': round(monthly_installment, 2)
        }

        response_serializer = LoanEligibilityResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def calculate_credit_score(self, customer):
        loans = Loan.objects.filter(customer=customer)

        if not loans.exists():
            return 60 

  
        total_emis_expected = loans.aggregate(Sum('tenure'))['tenure__sum'] or 0
        total_emis_paid = loans.aggregate(Sum('emis_paid_on_time'))['emis_paid_on_time__sum'] or 0
        emi_score = (total_emis_paid / total_emis_expected) * 25 if total_emis_expected > 0 else 0

   
        loan_count = loans.count()
        if loan_count <= 2:
            loan_count_score = 20
        elif loan_count <= 5:
            loan_count_score = 15
        elif loan_count <= 10:
            loan_count_score = 10
        else:
            loan_count_score = 5

   
        current_year = datetime.now().year
        activity_score = 20 if loans.filter(start_date__year=current_year).exists() else 0


        total_loan_amt = loans.aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
        if customer.approved_limit > 0:
            volume_ratio = total_loan_amt / customer.approved_limit
            if volume_ratio <= 0.5:
                volume_score = 20
            elif volume_ratio <= 1.0:
                volume_score = 15
            elif volume_ratio <= 1.5:
                volume_score = 10
            else:
                volume_score = 5
        else:
            volume_score = 0

    
        current_loans_amt = loans.filter(end_date__gte=date.today()).aggregate(Sum('loan_amount'))['loan_amount__sum'] or 0
        if current_loans_amt > customer.approved_limit:
            return 0

        total_score = emi_score + loan_count_score + activity_score + volume_score
        return round(min(total_score, 100))

    def check_loan_approval(self, customer, credit_score, loan_amount, interest_rate, tenure):
        current_loans = Loan.objects.filter(customer=customer, end_date__gte=date.today())
        current_emi = current_loans.aggregate(Sum('monthly_repayment'))['monthly_repayment__sum'] or 0

        projected_emi = self.calculate_monthly_installment(loan_amount, interest_rate, tenure)
        total_emi = current_emi + projected_emi

        if total_emi > customer.monthly_salary * 0.5:
            return False, interest_rate 

      
        if credit_score > 50:
            return True, interest_rate
        elif 30 < credit_score <= 50:
            if interest_rate >= 12:
                return True, interest_rate
            else:
                return True, 12  
        elif 10 < credit_score <= 30:
            if interest_rate >= 16:
                return True, interest_rate
            else:
                return True, 16  
        else:
            return False, interest_rate  

    def calculate_monthly_installment(self, loan_amount, annual_interest_rate, tenure_months):
        monthly_rate = annual_interest_rate / (12 * 100)
        if monthly_rate == 0:
            return loan_amount / tenure_months
        emi = loan_amount * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
        return emi



class CreateLoanView(APIView):
    def post(self, request):

        request_serializer = CreateLoanRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = request_serializer.validated_data
        customer_id = data['customer_id']
        loan_amount = data['loan_amount']
        interest_rate = data['interest_rate']
        tenure = data['tenure']
        
  
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
   
        eligibility_view = LoanEligibilityView()
        credit_score = eligibility_view.calculate_credit_score(customer)
        approval, corrected_interest_rate = eligibility_view.check_loan_approval(
            customer, credit_score, loan_amount, interest_rate, tenure
        )
        
    
        monthly_installment = eligibility_view.calculate_monthly_installment(
            loan_amount, corrected_interest_rate, tenure
        ) if approval else 0
        
        loan_id = None
        message = ""
        
        if approval:
     
            last_loan = Loan.objects.order_by('loan_id').last()
            loan_id = (last_loan.loan_id + 1) if last_loan else 1
            
            start_date = date.today()

            import calendar
            from dateutil.relativedelta import relativedelta
            end_date = start_date + relativedelta(months=tenure)
            
            try:
                Loan.objects.create(
                    loan_id=loan_id,
                    customer=customer,
                    loan_amount=loan_amount,
                    tenure=tenure,
                    interest_rate=corrected_interest_rate,
                    monthly_repayment=round(monthly_installment, 2),
                    emis_paid_on_time=0,
                    start_date=start_date,
                    end_date=end_date
                )
                message = "Loan approved successfully"
            except Exception as e:
                return Response(
                    {"error": f"Failed to create loan: {str(e)}"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        else:
            if credit_score <= 10:
                message = "Loan rejected due to low credit score"
            else:
                current_loans = Loan.objects.filter(
                    customer=customer, 
                    end_date__gte=date.today()
                )
                current_emi = current_loans.aggregate(Sum('monthly_repayment'))['monthly_repayment__sum'] or 0
                
                if current_emi > (customer.monthly_salary * 0.5):
                    message = "Loan rejected due to high existing EMI burden"
                else:
                    message = "Loan rejected based on credit assessment"
        
        response_data = {
            'loan_id': loan_id,
            'customer_id': customer_id,
            'loan_approved': approval,
            'message': message,
            'monthly_installment': round(monthly_installment, 2) if approval else 0.0
        }
        
        response_serializer = CreateLoanResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_201_CREATED if approval else status.HTTP_200_OK)
        return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ViewLoanView(APIView):
    def get(self, request, loan_id):
        """View details of a specific loan"""
        try:
            loan = Loan.objects.select_related('customer').get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response(
                {"error": "Loan not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_data = {
            'loan_id': loan.loan_id,
            'customer': {
                'id': loan.customer.customer_id,
                'first_name': loan.customer.first_name,
                'last_name': loan.customer.last_name,
                'phone_number': loan.customer.phone_number,
                'age': loan.customer.age
            },
            'loan_amount': loan.loan_amount,
            'interest_rate': loan.interest_rate,
            'monthly_installment': loan.monthly_repayment,
            'tenure': loan.tenure
        }
        
        response_serializer = ViewLoanResponseSerializer(data=response_data)
        if response_serializer.is_valid():
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        return Response(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ViewLoansView(APIView):
    def get(self, request, customer_id):
        """View all loans for a specific customer"""
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        loans = Loan.objects.filter(customer=customer)
        
        if not loans.exists():
            return Response([], status=status.HTTP_200_OK)
        
        loans_data = []
        for loan in loans:
            repayments_left = max(0, loan.tenure - loan.emis_paid_on_time)
            
            loan_data = {
                'loan_id': loan.loan_id,
                'loan_amount': loan.loan_amount,
                'interest_rate': loan.interest_rate,
                'monthly_installment': loan.monthly_repayment,
                'repayments_left': repayments_left
            }
            loans_data.append(loan_data)
        
        serialized_loans = []
        for loan_data in loans_data:
            loan_serializer = ViewLoansResponseSerializer(data=loan_data)
            if loan_serializer.is_valid():
                serialized_loans.append(loan_serializer.data)
            else:
                return Response(loan_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serialized_loans, status=status.HTTP_200_OK)
