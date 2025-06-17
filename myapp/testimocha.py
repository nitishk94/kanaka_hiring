from datetime import datetime
from flask import jsonify, request
from models.testresult import TestResult
from models.applicants import Applicant
from models.recruitment_history import RecruitmentHistory
from extensions import db

import requests


def store_result(id):
    applicant = Applicant.query.get_or_404(id)
    history = RecruitmentHistory.query.filter_by(applicant_id=id).first()
    testInviteid = history.test_id

    api_url="https://apiv3.imocha.io/v3/reports/"+str(testInviteid)+"?reportType=1"
    headers = {
        "X-API-KEY": "MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }
    
    response = requests.get(api_url, headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get('status') == 'Complete':
            test_result = TestResult(
                testlink_id=testInviteid,
                name=applicant.name,
                email=result['candidateEmail'],
                date = datetime.strptime(result['attemptedOn'], '%Y-%m-%dT%H:%M:%S.%fZ').date(),
                score=result['candidatePoints'],
                total_score=result['totalTestPoints'],
                time_taken=result['timeTaken']/60,
                test_time=result['testDuration'],
                test_name=result['testName'],
                pdf_link=result['pdfReportUrl'],
                sections=str(result['sections']),
                applicant_id=id
            )
            db.session.add(test_result)
            history.test_result = True
            db.session.commit()
            return True
    else:
        return False
    

def list_tests():
    url_for="https://apiv3.imocha.io/v3/tests"
    headers = {
        "X-API-KEY":"MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type":"application/json"
    }
    response = requests.get(url_for, headers=headers)
    result=response.json()
    return result['tests'][0]['testId']

def invite_candidate(testId):
    
    data = {
        "name": "Vatsa",
        "email": "tarineepawar@gmail.com",
        "sendEmail" : "yes",
        "stakeholderEmails":"shrivatsa26@gmail.com",
        "startDateTime": "2025-06-16T06:30:00Z",
        "endDateTime": "2025-06-17T12:00:00Z",
        "timeZoneId": 1720,
        "ProctoringMode": "disabled"
    }
    url_for="https://apiv3.imocha.io/v3/tests/"+str(testId)+"/invite"
    headers = {
        "X-API-KEY":"MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }

    response = requests.post(url_for, headers=headers, json=data)
    response_data = response.json()
    return response_data

def test_result(testInviteid):
    
    url_for="https://apiv3.imocha.io/v3/reports/"+str(testInviteid)+"?reportType=1"
    headers = {
        "X-API-KEY":"MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }

    response = requests.get(url_for, headers=headers)
    result = response.json()

    return result

def get_test_links(testId):
    url = f"https://apiv3.imocha.io/v3/tests/"+str(testId)+"/testlinks"
    headers = {
        "X-API-KEY": "MLgDuuMLvhyRcoHxmaGBBHxBItiKrb",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers)
    result = response.json()
    return result
      

def main():
    testId = list_tests()
    print(f"Test ID: {testId}")
    
    if testId:
        #invite_response = invite_candidate(testId)
        #print(f"Invite Response: {invite_response}")
        #testInvitationId = invite_response.get('testInvitationId')
        #print(f"Test Invitation ID: {testInvitationId}")
        print(store_result(2))

    else:
        print("No tests found.")
       
if __name__ == '__main__':
    main()