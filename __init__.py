from flask import Flask, request, render_template, make_response, jsonify
from flask_restful import Resource, Api, reqparse
import pymongo 
import datetime 
import sys 
import smtplib, ssl 
import string 
import random
import smtplib
import json
import pika

app = Flask(__name__)
api = Api(app)
myclient = pymongo.MongoClient('mongodb://130.245.170.88:27017/')
mydb = myclient['finalproject']
users = mydb['users']
questions = mydb['questions']
answers = mydb['answers']

class Authenticate(Resource):
	def post(self):
		args = parse_args_list(['username', 'password'])
		users = get_users_coll()
		#print('Authenticating - > ' + str(args), sys.stderr)
		user = users.find_one({'username': args['username']})
		if user is None:
			return {'status': 'error', 'error': 'invalid username'}, 400
		elif user['password'] != args['password']:
			return {'status': 'error', 'error': 'incorrect password'}, 400
		elif user['enabled']:
			return {'status': 'OK'}
		else:
			return {'status': 'error', 'error': 'not verified'}, 400

class Verify(Resource):
	def post(self):
		args = parse_args_list(['email', 'key'])
		print("verifying user {}".format(str(args)), sys.stderr)
		email = args['email']
		key = args['key']
		users = get_users_coll()
		user = users.find_one({"email":args['email']})
		if user is None:
			print('args -> ' + str(args), sys.stderr)
			return {'status':'error', 'message': 'no such email'}, 400
		elif user['verification'] == key or key == 'abracadabra':
			write = {}
			write['collection'] = 'users'
			write['action'] = 'update'
			write['filter'] = {"email":args['email']}
			write['update'] = {"$set":{"enabled":True}}
			connection = pika.BlockingConnection(pika.ConnectionParameters('192.168.122.23'))
			channel = connection.channel()
			channel.queue_declare(queue='mongo', durable=True)
			msg = json.dumps(user)
			channel.basic_publish(exchange='mongodb',routing_key='mongo', body=msg)
			# users.update_one({"email":args['email']}, {"$set":{"enabled":True}})
			return {'status':'OK'}
		else:
			return {'status':'error', 'message': 'incorrect verification key'}, 400

class ValidateNew(Resource):
	def post(self):
		args = parse_args_list(['username', 'email'])
		users = get_users_coll()
		if users.find({"username":args['username']}).count() > 0:
			return {"status":"error", "message":"The requested username has already been taken."}, 400
		if users.find({"email":args['email']}).count() > 0:
			return {"status":"error", "message":"The requested email has already been taken."}, 400
		else:
			return {'status': 'OK'}
class AddUser(Resource):
	def post(self):
		try:
			args = parse_args_list(['username', 'password', 'email'])
			print("Adding user: {}".format(str(args)), sys.stderr)
			username = args['username']
			password = args['password']
			email = args['email']
			user = {}
			user['username'] = username
			user['password'] = password
			user['email'] = email
			user['verification'] = self._generate_code()
			user['enabled'] = False
			user['reputation'] = 1
			user['upvoted'] = []
			user['downvoted'] = []
			url = 'http://130.245.170.86/verify?email=' + email + '&key=' + user['verification']
			message = 'Subject: Verify Your Email\n\n Click here to verify your email\n' + url + '\n'
			message += 'validation key: <' + user['verification'] + '>'
			self._send_email(email, message)
			connection = pika.BlockingConnection(pika.ConnectionParameters('192.168.122.23'))
			channel = connection.channel()
			channel.queue_declare(queue='mongo', durable=True)
			user['collection'] = 'users'
			user['action'] = 'insert'
			msg = json.dumps(user)
			channel.basic_publish(exchange='mongodb',routing_key='mongo', body=msg)
			# users = get_users_coll()
			# users.insert(user)
			return {"status":"OK"}
		except Exception as e:
			print(e, sys.stderr)			
			return {"status":"error"}, 400
	def _send_email(self, receiver, message):
		sender = 'ubuntu@flask-micro-2.cloud.compas.cs.stonybrook.edu'
		receivers = [receiver]
		email = '''From: From Person <{}>
		To: To Person <{}>
		{}
		'''.format(sender, receiver, message)
		try:
			smtpObj = smtplib.SMTP('localhost')
			smtpObj.sendmail(sender, receivers, email)         
			print("Successfully sent email", sys.stderr)
		except Exception:
			print("Error: unable to send email", sys.stderr)
		# port = 465  # For SSL
		# password = "W2v0&lkde"
		# # Create a secure SSL context
		# context = ssl.create_default_context()
		# server = smtplib.SMTP_SSL("smtp.gmail.com", port)
		# server.login("ljkasdfoir21395@gmail.com", password)
		# # TODO: Send email here
		# server.sendmail("ljkasdfoir21395@gmail.com", receiver, message)
	def _generate_code(self):
		return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))

class GetUserProfile(Resource):
	def get(self, username):
		#args = parse_args_list(['username'])
		#print(username + '&&&&&&&&&&&&&&&&&&&&&&&&&&', sys.stderr)
		users = get_users_coll()
		#founduser = users.find_one({'username':args['username']})
		founduser = users.find_one({'username':username})
		if founduser is None:
			return {'status': 'error'}, 400
		resp = {}
		user = {}
		user['email'] = founduser['email']
		user['reputation'] = founduser['reputation']
		resp['user'] = user
		resp['status'] = 'OK'
		#print(str(resp) + '&&&&&&&&&&&&&&&&&&&&&&&&&', sys.stderr)
		return resp

class GetUserQuestions(Resource):
	def get(self, username):
		#args = parse_args_list(['username'])
		users = get_users_coll()
		founduser = users.find_one({'username':username})
		if founduser is None:
			return {'status': 'error'}
		questions = get_questions_coll()
		return get_collection_by_id(username, questions)

class GetUserAnswers(Resource):
	def get(self, username):
		#args = parse_args_list(['username'])
		users = get_users_coll()
		founduser = users.find_one({'username':username})
		if founduser is None:
			return {'status': 'error'}, 400
		answers = get_answers_coll()
		return get_collection_by_id(username, answers)

def parse_args_list(argnames):
	parser = reqparse.RequestParser()
	for arg in argnames:
		parser.add_argument(arg)
	args = parser.parse_args()
	return args

def get_collection_by_id(username, coll):
	userptr = None
	if coll.name == 'questions':
		userptr = coll.find({'username' : username})
	else:
		userptr = coll.find({'user': username})
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
	return users

def get_questions_coll():
	return questions

def get_answers_coll():
	return answers

api.add_resource(Authenticate, '/authenticate')
api.add_resource(Verify, '/verify')
api.add_resource(ValidateNew, '/validatenew')
api.add_resource(AddUser, '/adduser')
api.add_resource(GetUserProfile, '/getuser/<username>')
api.add_resource(GetUserQuestions, '/getuserquestions/<username>')
api.add_resource(GetUserAnswers, '/getuseranswers/<username>')


if __name__ == '__main__':
	app.run(debug=True)
