from flask import jsonify, request
import requests

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
    
    url_for="https://apiv3.imocha.io/v3/reports/"+str(testInviteid)+"?reportType=3"
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
        print(invite_candidate(131310890))

    else:
        print("No tests found.")
       
if __name__ == '__main__':
    main()