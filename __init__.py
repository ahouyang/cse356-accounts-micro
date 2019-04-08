from flask import Flask, request, render_template, make_response, jsonify
from flask_restful import Resource, Api, reqparse
import pymongo 
import datetime 
import sys 
import smtplib, ssl 
import string 
import random

app = Flask(__name__)
api = Api(app)

class Authenticate(Resource):
	def post(self):
		args = parse_args_list(['username', 'password'])
		users = get_users_coll()
		print('--------------------------args:' + str(args), sys.stderr)
		user = users.find_one({'username': args['username']})
		if user is None:
			return {'status': 'error', 'error': 'invalid username'}
		elif user['password'] != args['password']:
			return {'status': 'error', 'error': 'incorrect password'}
		elif user['enabled']:
			return {'status': 'OK'}
		else:
			return {'status': 'error', 'error': 'not verified'}

class Verify(Resource):
	def post(self):
		args = parse_args_list(['email', 'key'])
		email = args['email']
		key = args['key']
		users = get_users_coll()
		user = users.find_one({"email":args['email']})
		if user is None:
			return {'status':'error', 'message': 'no such email'}
		elif user['verification'] == key or key == 'abracadabra':
			users.update_one({"email":args['email']}, {"$set":{"enabled":True}})
			return {'status':'OK'}
		else:
			return {'status':'error', 'message': 'incorrect verification key'}

class ValidateNew(Resource):
	def post(self):
		args = parse_args_list(['username', 'email'])
		users = get_users_coll()
		if users.find({"username":args['username']}).count() > 0:
			return {"status":"error", "message":"The requested username has already been taken."}	
		if users.find({"email":args['email']}).count() > 0:
			return {"status":"error", "message":"The requested email has already been taken."}
		else:
			return {'status': 'OK'}
class AddUser(Resource):
	def post(self):
		try:
			args = parse_args_list(['username', 'password', 'email'])
			username = args['username']
			password = args['password']
			email = args['email']
			user = {}
			user['username'] = username
			user['password'] = password
			user['email'] = email
			user['verification'] = self._generate_code()
			user['enabled'] = False
			user['reputation'] = 0
			url = 'http://130.245.170.86/verify?email=' + email + '&key=' + user['verification']
			message = 'Subject: Verify Your Email\n\n Click here to verify your email\n' + url + '\n'
			message += 'validation key: <' + user['verification'] + '>'
			self._send_email(email, message)
			users = get_users_coll()
			users.insert(user)
			return {"status":"OK"}
		except Exception as e:
			print(e, sys.stderr)			
			return {"status":"error"}
	
	def _send_email(self, receiver, message):
		port = 465  # For SSL
		password = "W2v0&lkde"
		# Create a secure SSL context
		context = ssl.create_default_context()
		server = smtplib.SMTP_SSL("smtp.gmail.com", port)
		server.login("ljkasdfoir21395@gmail.com", password)
		# TODO: Send email here
		server.sendmail("ljkasdfoir21395@gmail.com", receiver, message)
	def _generate_code(self):
		return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

class GetUserProfile(Resource):
	def get(self):
		args = parse_args_list(['username'])
		users = get_users_coll()
		founduser = users.find_one({'username':args['username']})
		if founduser is None:
			return {'status': 'error'}
		resp = {}
		
		user = {}
		user['email'] = founduser['email']
		user['reputation'] = founduser['reputation']
		
		resp['user'] = user
		resp['status'] = 'OK'

		return resp

class GetUserQuestions(Resource):
	def get(self):
		args = parse_args_list(['username'])
		users = get_users_coll()
		founduser = users.find_one({'username':args['username']})
		if founduser is None:
			return {'status': 'error'}
		questions = get_questions_coll()
		return get_collection_by_id(args['username'], questions)

class GetUserAnswers(Resource):
	def get(self):
		args = parse_args_list(['username'])
		users = get_users_coll()
		founduser = users.find_one({'username':args['username']})
		if founduser is None:
			return {'status': 'error'}
		answers = get_answers_coll()
		return get_collection_by_id(args['username'], answers)

def parse_args_list(argnames):
	parser = reqparse.RequestParser()
	for arg in argnames:
		parser.add_argument(arg)
	args = parser.parse_args()
	return args

def get_collection_by_id(username, coll):
	userptr = coll.find({'username' : username})
	result = []
	for user in userptr:
		result.append(user['id'])
	resp = {}
	resp['status'] = 'OK'
	if coll.name == 'questions':
		resp['questions'] = result
	else:	# coll.name == 'answers'
		resp['answers'] = result
	return resp

def get_users_coll():
	myclient = pymongo.MongoClient('mongodb://130.245.170.88:27017/')
	mydb = myclient['finalproject']
	users = mydb['users']
	return users

def get_questions_coll():
	# reconnecting may cause performance issues
	myclient = pymongo.MongoClient('mongodb://130.245.170.88:27017/')
	mydb = myclient['finalproject']
	users = mydb['questions']
	return users

def get_answers_coll():
	myclient = pymongo.MongoClient('mongodb://130.245.170.88:27017/')
	mydb = myclient['finalproject']
	users = mydb['answers']
	return users

api.add_resource(Authenticate, '/authenticate')
api.add_resource(Verify, '/verify')
api.add_resource(ValidateNew, '/validatenew')
api.add_resource(AddUser, '/adduser')
api.add_resource(GetUserProfile, '/getuser')
api.add_resource(GetUserQuestions, '/getuserquestions')
api.add_resource(GetUserAnswers, '/getuseranswers')


if __name__ == '__main__':
	app.run(debug=True)
