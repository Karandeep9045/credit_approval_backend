from celery import shared_task
import pandas as pd
from .models import Customer, Loan
from django.utils.dateparse import parse_date
from django.db import transaction
import os
from django.conf import settings

@shared_task
def ingest_data():
    try:
        customer_file = os.path.join(settings.BASE_DIR, 'data', 'customer_data.xlsx')
        loan_file = os.path.join(settings.BASE_DIR, 'data', 'loan_data.xlsx')
        
        if not os.path.exists(customer_file) or not os.path.exists(loan_file):
            return f"Data files not found: customer={os.path.exists(customer_file)}, loan={os.path.exists(loan_file)}"

        try:
            customer_df = pd.read_excel(customer_file)
        except Exception as e:
            return f"Error reading customer file: {str(e)}"
        
        customer_column_mapping = {}
        for col in customer_df.columns:
            col_lower = col.lower().strip()
            if 'customer' in col_lower and 'id' in col_lower:
                customer_column_mapping[col] = 'customer_id'
            elif 'first' in col_lower and 'name' in col_lower:
                customer_column_mapping[col] = 'first_name'
            elif 'last' in col_lower and 'name' in col_lower:
                customer_column_mapping[col] = 'last_name'
            elif 'age' in col_lower:
                customer_column_mapping[col] = 'age'
            elif 'phone' in col_lower:
                customer_column_mapping[col] = 'phone_number'
            elif 'salary' in col_lower:
                customer_column_mapping[col] = 'monthly_salary'
            elif 'limit' in col_lower:
                customer_column_mapping[col] = 'approved_limit'
        
        try:
            customer_df = customer_df.rename(columns=customer_column_mapping)
        except Exception as e:
            return f"Error renaming customer columns: {str(e)}"

        try:
            loan_df = pd.read_excel(loan_file)
        except Exception as e:
            return f"Error reading loan file: {str(e)}"
        
        loan_column_mapping = {}
        for col in loan_df.columns:
            col_lower = col.lower().strip()
            if 'customer' in col_lower and 'id' in col_lower:
                loan_column_mapping[col] = 'customer_id'
            elif 'loan' in col_lower and 'id' in col_lower:
                loan_column_mapping[col] = 'loan_id'
            elif 'loan' in col_lower and 'amount' in col_lower:
                loan_column_mapping[col] = 'loan_amount'
            elif 'tenure' in col_lower:
                loan_column_mapping[col] = 'tenure'
            elif 'interest' in col_lower and 'rate' in col_lower:
                loan_column_mapping[col] = 'interest_rate'
            elif 'monthly' in col_lower and 'payment' in col_lower:
                loan_column_mapping[col] = 'monthly_payment'
            elif 'emis' in col_lower and ('paid' in col_lower or 'time' in col_lower):
                loan_column_mapping[col] = 'emis_paid_on_time'
            elif ('start' in col_lower and 'date' in col_lower) or ('date' in col_lower and 'approval' in col_lower):
                loan_column_mapping[col] = 'start_date'
            elif 'end' in col_lower and 'date' in col_lower:
                loan_column_mapping[col] = 'end_date'
        
        try:
            loan_df = loan_df.rename(columns=loan_column_mapping)
        except Exception as e:
            return f"Error renaming loan columns: {str(e)}"

        required_customer_cols = ['customer_id', 'first_name', 'last_name', 'phone_number', 'monthly_salary', 'approved_limit']
        required_loan_cols = ['customer_id', 'loan_id', 'loan_amount', 'tenure', 'interest_rate', 'monthly_payment', 'emis_paid_on_time', 'start_date', 'end_date']
        
        missing_customer_cols = [col for col in required_customer_cols if col not in customer_df.columns]
        missing_loan_cols = [col for col in required_loan_cols if col not in loan_df.columns]
        
        if missing_customer_cols:
            return f"Missing customer columns: {missing_customer_cols}. Available: {list(customer_df.columns)}"
        if missing_loan_cols:
            return f"Missing loan columns: {missing_loan_cols}. Available: {list(loan_df.columns)}"

        with transaction.atomic():
            Customer.objects.all().delete()
            Loan.objects.all().delete()
            
            customer_df = customer_df.drop_duplicates(subset=['customer_id'], keep='first')
            loan_df = loan_df.drop_duplicates(subset=['loan_id'], keep='first')

            for idx, row in customer_df.iterrows():
                try:
                    Customer.objects.create(
                        customer_id=int(row['customer_id']),
                        first_name=str(row['first_name']).strip(),
                        last_name=str(row['last_name']).strip(),
                        phone_number=int(row['phone_number']),
                        monthly_salary=float(row['monthly_salary']),
                        approved_limit=float(row['approved_limit']),
                        age=int(row['age']) if not pd.isna(row['age']) else None,
                    )
                except Exception as e:
                    return f"Error creating customer {row.get('customer_id', 'unknown')}: {str(e)}"

            loans_created = 0
            loans_skipped = 0
            
            for idx, row in loan_df.iterrows():
                try:
                    customer = Customer.objects.get(customer_id=int(row['customer_id']))
                    
                    start_date = None
                    end_date = None
                    
                    if not pd.isna(row['start_date']):
                        start_date_str = str(row['start_date'])
                        if start_date_str and start_date_str != 'nan':
                            if len(start_date_str) == 10 and start_date_str.count('-') == 2:
                                start_date = parse_date(start_date_str)
                            else:
                                try:
                                    start_date = pd.to_datetime(row['start_date']).date()
                                except:
                                    pass
                    
                    if not pd.isna(row['end_date']):
                        end_date_str = str(row['end_date'])
                        if end_date_str and end_date_str != 'nan':
                            if len(end_date_str) == 10 and end_date_str.count('-') == 2:
                                end_date = parse_date(end_date_str)
                            else:
                                try:
                                    end_date = pd.to_datetime(row['end_date']).date()
                                except:
                                    pass
                    
                    if start_date is None or end_date is None:
                        loans_skipped += 1
                        continue
                    
                    Loan.objects.create(
                        customer=customer,
                        loan_id=int(row['loan_id']),
                        loan_amount=float(row['loan_amount']),
                        tenure=int(row['tenure']),
                        interest_rate=float(row['interest_rate']),
                        monthly_repayment=float(row['monthly_payment']),
                        emis_paid_on_time=int(row['emis_paid_on_time']),
                        start_date=start_date,
                        end_date=end_date,
                    )
                    loans_created += 1
                    
                except Customer.DoesNotExist:
                    loans_skipped += 1
                    continue
                except Exception as e:
                    return f"Error creating loan {row.get('loan_id', 'unknown')}: {str(e)}"

        return f"Ingestion complete: {Customer.objects.count()} customers, {loans_created} loans" + (f", {loans_skipped} skipped" if loans_skipped > 0 else "")

    except Exception as e:
        return f"Ingestion failed: {str(e)}"
