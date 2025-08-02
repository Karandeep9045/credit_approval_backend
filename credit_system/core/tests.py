from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from datetime import date, datetime
import json

from .models import Customer, Loan
from .views import LoanEligibilityView
from .tasks import ingest_data


class CustomerModelTest(TestCase):
    """Test Customer model functionality"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
    
    def test_customer_creation(self):
        """Test customer model creation"""
        self.assertEqual(self.customer.first_name, "Test")
        self.assertEqual(self.customer.last_name, "User")
        self.assertEqual(self.customer.phone_number, 9999999999)
        self.assertEqual(self.customer.monthly_salary, 50000)
        self.assertEqual(self.customer.approved_limit, 1800000)
        self.assertEqual(self.customer.age, 30)
    
    def test_customer_str_method(self):
        """Test customer string representation"""
        expected_str = "Test User"
        self.assertEqual(str(self.customer), expected_str)
    
    def test_customer_unique_phone(self):
        """Test unique phone number constraint"""
        with self.assertRaises(Exception):
            Customer.objects.create(
                customer_id=2,
                first_name="Another",
                last_name="User",
                phone_number=9999999999, 
                monthly_salary=60000,
                approved_limit=2000000,
                age=25
            )


class LoanModelTest(TestCase):
    """Test Loan model functionality"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
        
        self.loan = Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=500000,
            tenure=24,
            interest_rate=10.5,
            monthly_repayment=23188.02,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date(2027, 1, 25)
        )
    
    def test_loan_creation(self):
        """Test loan model creation"""
        self.assertEqual(self.loan.loan_id, 1)
        self.assertEqual(self.loan.customer, self.customer)
        self.assertEqual(self.loan.loan_amount, 500000)
        self.assertEqual(self.loan.tenure, 24)
        self.assertEqual(self.loan.interest_rate, 10.5)
        self.assertEqual(self.loan.monthly_repayment, 23188.02)
    
    def test_loan_str_method(self):
        """Test loan string representation"""
        expected_str = "Loan #1 for Test"
        self.assertEqual(str(self.loan), expected_str)
    
    def test_loan_customer_relationship(self):
        """Test loan-customer foreign key relationship"""
        self.assertEqual(self.loan.customer.customer_id, 1)
        self.assertEqual(self.customer.loans.first(), self.loan)


class RegisterCustomerAPITest(APITestCase):
    """Test customer registration API endpoint"""
    
    def setUp(self):
        self.url = reverse('register-customer')
        self.valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "9876543210",
            "monthly_income": 75000,
            "age": 28
        }
    
    def test_register_customer_success(self):
        """Test successful customer registration"""
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)
        self.assertIn('name', response.data)
        self.assertIn('approved_limit', response.data)
        
       
        expected_limit = round((36 * 75000) / 100000) * 100000
        self.assertEqual(response.data['approved_limit'], expected_limit)
    
    def test_register_customer_duplicate_phone(self):
        """Test duplicate phone number rejection"""
     
        self.client.post(self.url, self.valid_data, format='json')
        
      
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)
    
    def test_register_customer_invalid_data(self):
        """Test registration with invalid data"""
        invalid_data = {
            "first_name": "",  
            "last_name": "Doe",
            "phone_number": "invalid_phone",
            "monthly_income": -1000,  
            "age": -5 
        }
        
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoanEligibilityAPITest(APITestCase):
    """Test loan eligibility checking API endpoint"""
    
    def setUp(self):
        self.url = reverse('check-eligibility')
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
        
        self.valid_data = {
            "customer_id": 1,
            "loan_amount": 500000,
            "interest_rate": 10.0,
            "tenure": 24
        }
    
    def test_eligibility_check_new_customer(self):
        """Test eligibility for customer with no loan history"""
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('approval', response.data)
        self.assertIn('interest_rate', response.data)
        self.assertIn('corrected_interest_rate', response.data)
        self.assertIn('monthly_installment', response.data)
        
       
        self.assertFalse(response.data['approval'])
    
    def test_eligibility_check_nonexistent_customer(self):
        """Test eligibility for non-existent customer"""
        invalid_data = self.valid_data.copy()
        invalid_data['customer_id'] = 99999
        
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_eligibility_check_invalid_data(self):
        """Test eligibility with invalid request data"""
        invalid_data = {
            "customer_id": "invalid",
            "loan_amount": -1000,
            "interest_rate": -5,
            "tenure": 0
        }
        
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CreateLoanAPITest(APITestCase):
    """Test loan creation API endpoint"""
    
    def setUp(self):
        self.url = reverse('create-loan')
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
        
        self.valid_data = {
            "customer_id": 1,
            "loan_amount": 500000,
            "interest_rate": 10.0,
            "tenure": 24
        }
    
    def test_create_loan_new_customer_rejection(self):
        """Test loan creation rejection for new customer"""
        response = self.client.post(self.url, self.valid_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('loan_approved', response.data)
        self.assertIn('message', response.data)
        self.assertIn('monthly_installment', response.data)
        
       
        self.assertFalse(response.data['loan_approved'])
        self.assertIsNone(response.data['loan_id'])
    
    def test_create_loan_nonexistent_customer(self):
        """Test loan creation for non-existent customer"""
        invalid_data = self.valid_data.copy()
        invalid_data['customer_id'] = 99999
        
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ViewLoanAPITest(APITestCase):
    """Test loan viewing API endpoints"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
        
        self.loan = Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=500000,
            tenure=24,
            interest_rate=10.5,
            monthly_repayment=23188.02,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date(2027, 1, 25)
        )
    
    def test_view_loan_success(self):
        """Test viewing specific loan details"""
        url = reverse('view-loan', kwargs={'loan_id': 1})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('loan_id', response.data)
        self.assertIn('customer', response.data)
        self.assertIn('loan_amount', response.data)
        self.assertIn('monthly_installment', response.data)
        
        self.assertEqual(response.data['loan_id'], 1)
        self.assertEqual(response.data['customer']['id'], 1)
        self.assertEqual(response.data['loan_amount'], 500000)
    
    def test_view_loan_not_found(self):
        """Test viewing non-existent loan"""
        url = reverse('view-loan', kwargs={'loan_id': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_view_loans_success(self):
        """Test viewing customer's loans"""
        url = reverse('view-loans', kwargs={'customer_id': 1})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)
        
        loan_data = response.data[0]
        self.assertIn('loan_id', loan_data)
        self.assertIn('repayments_left', loan_data)
        self.assertEqual(loan_data['loan_id'], 1)
    
    def test_view_loans_empty(self):
        """Test viewing loans for customer with no loans"""
        customer2 = Customer.objects.create(
            customer_id=2,
            first_name="Another",
            last_name="User",
            phone_number=8888888888,
            monthly_salary=60000,
            approved_limit=2000000,
            age=25
        )
        
        url = reverse('view-loans', kwargs={'customer_id': 2})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
    
    def test_view_loans_nonexistent_customer(self):
        """Test viewing loans for non-existent customer"""
        url = reverse('view-loans', kwargs={'customer_id': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CreditScoreCalculationTest(TestCase):
    """Test credit score calculation logic"""
    
    def setUp(self):
        self.customer = Customer.objects.create(
            customer_id=1,
            first_name="Test",
            last_name="User",
            phone_number=9999999999,
            monthly_salary=50000,
            approved_limit=1800000,
            age=30
        )
        
        self.view = LoanEligibilityView()
    
    def test_credit_score_no_history(self):
        """Test credit score for customer with no loan history"""
        score = self.view.calculate_credit_score(self.customer)
        self.assertEqual(score, 0)
    
    def test_credit_score_with_good_history(self):
        """Test credit score for customer with good loan history"""
      
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=300000,
            tenure=24,
            interest_rate=10.0,
            monthly_repayment=14000,
            emis_paid_on_time=24,  
            start_date=date(2022, 1, 1),
            end_date=date(2024, 1, 1)
        )
        
        score = self.view.calculate_credit_score(self.customer)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)
    
    def test_credit_score_exceeds_limit(self):
        """Test credit score when current loans exceed approved limit"""
       
        Loan.objects.create(
            loan_id=1,
            customer=self.customer,
            loan_amount=2000000, 
            tenure=24,
            interest_rate=10.0,
            monthly_repayment=90000,
            emis_paid_on_time=0,
            start_date=date.today(),
            end_date=date(2026, 1, 25)
        )
        
        score = self.view.calculate_credit_score(self.customer)
        self.assertEqual(score, 0)


class DataIngestionTaskTest(TransactionTestCase):
    """Test Celery data ingestion task"""
    
    @patch('core.tasks.pd.read_excel')
    @patch('core.tasks.os.path.exists')
    def test_ingest_data_success(self, mock_exists, mock_read_excel):
        """Test successful data ingestion"""
       
        mock_exists.return_value = True
        
       
        import pandas as pd
        
        
        customer_data = {
            'Customer ID': [1],
            'First Name': ['Test'],
            'Last Name': ['User'],
            'Age': [30],
            'Phone Number': [9999999999],
            'Monthly Salary': [50000],
            'Approved Limit': [1800000]
        }
        mock_customer_df = pd.DataFrame(customer_data)
        
        
        loan_data = {
            'Customer ID': [1],
            'Loan ID': [1],
            'Loan Amount': [500000],
            'Tenure': [24],
            'Interest Rate': [10.0],
            'Monthly payment': [23000],
            'EMIs paid on Time': [0],
            'Date of Approval': ['2025-01-25'],
            'End Date': ['2027-01-25']
        }
        mock_loan_df = pd.DataFrame(loan_data)
        
      
        mock_read_excel.side_effect = [mock_customer_df, mock_loan_df]
        
       
        result = ingest_data()
        
       
        self.assertIn("Ingestion complete", result)
    
    @patch('core.tasks.os.path.exists')
    def test_ingest_data_file_not_found(self, mock_exists):
        """Test ingestion when files don't exist"""
        mock_exists.return_value = False
        
        result = ingest_data()
        self.assertIn("Data files not found", result)


class MonthlyInstallmentCalculationTest(TestCase):
    """Test monthly installment calculation"""
    
    def setUp(self):
        self.view = LoanEligibilityView()
    
    def test_monthly_installment_calculation(self):
        """Test compound interest EMI calculation"""
        loan_amount = 500000
        annual_interest_rate = 12.0
        tenure_months = 24
        
        emi = self.view.calculate_monthly_installment(
            loan_amount, annual_interest_rate, tenure_months
        )
        
       
        self.assertGreater(emi, 0)
        self.assertLess(emi, loan_amount) 
    
    def test_monthly_installment_zero_interest(self):
        """Test EMI calculation with zero interest rate"""
        loan_amount = 500000
        annual_interest_rate = 0.0
        tenure_months = 24
        
        emi = self.view.calculate_monthly_installment(
            loan_amount, annual_interest_rate, tenure_months
        )
        
   
        expected_emi = loan_amount / tenure_months
        self.assertAlmostEqual(emi, expected_emi, places=2)


class IntegrationTest(APITestCase):
    """Integration tests for complete workflows"""
    
    def test_complete_customer_loan_workflow(self):
        """Test complete workflow: register customer -> check eligibility -> create loan -> view loan"""
        
     
        register_url = reverse('register-customer')
        customer_data = {
            "first_name": "Integration",
            "last_name": "Test",
            "phone_number": "7777777777",
            "monthly_income": 100000,
            "age": 35
        }
        
        register_response = self.client.post(register_url, customer_data, format='json')
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        customer_id = register_response.data['customer_id']
        
     
        eligibility_url = reverse('check-eligibility')
        eligibility_data = {
            "customer_id": customer_id,
            "loan_amount": 500000,
            "interest_rate": 10.0,
            "tenure": 24
        }
        
        eligibility_response = self.client.post(eligibility_url, eligibility_data, format='json')
        self.assertEqual(eligibility_response.status_code, status.HTTP_200_OK)
        
   
        create_loan_url = reverse('create-loan')
        create_response = self.client.post(create_loan_url, eligibility_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_200_OK)
        self.assertFalse(create_response.data['loan_approved'])
        
    
        view_loans_url = reverse('view-loans', kwargs={'customer_id': customer_id})
        view_response = self.client.get(view_loans_url)
        self.assertEqual(view_response.status_code, status.HTTP_200_OK)
        self.assertEqual(view_response.data, [])
