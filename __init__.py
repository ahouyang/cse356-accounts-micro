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
		user = users.find_one({'username': args['username']})
		if user is None:
			return {'status': 'ERROR', 'message': 'invalid username'}
		elif user['password'] != args['password']:
			return {'status': 'ERROR', 'message': 'incorrect password'}
		elif user['enabled']:
			return {'status': 'OK'}
		else:
			return {'status': 'ERROR', 'message': 'not verified'}

class Verify(Resource):
	def post(self):
		args = parse_args_list(['email', 'key'])
		email = args['email']
		key = args['key']
		users = get_users_coll()
		user = users.find_one({"email":email})
		if user is None:
			return {'status':'ERROR', 'message': 'no such email'}
		elif user['verification'] == key or key == 'abracadabra':
			users.update_one({"email":email}, {"$set":{"enabled":True}})
			return {'status':'OK'}
		else:
			return {'status':'ERROR', 'message': 'incorrect verification key'}

class ValidateNew(Resource):
	def post(self):
		args = parse_args_list(['username', 'email'])
		users = get_users_coll()
		if users.find({"username":username}).count() > 0:
			return {"status":"ERROR", "message":"The requested username has already been taken."}	
		if users.find({"email":email}).count() > 0:
			return {"status":"ERROR", "message":"The requested email has already been taken."}
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
			user['games'] = []
			game = {}
			now = datetime.datetime.now()
			month = str(now.month) if len(str(now.month)) == 2 else '0' + str(now.month)
			day = str(now.day) if len(str(now.day)) == 2 else '0' + str(now.day)
			date = str(now.year) + '-' + month + '-' + day
			game['id'] = 1
			game['start_date'] = date
			game['grid'] = [" "," "," "," "," "," "," "," "," "]
			# user['games'].append(game)
			user['current_game'] = game
			user['score'] = {}
			user['score']['wins'] = 0
			user['score']['wgor'] = 0
			user['score']['tie'] = 0
			url = 'http://130.245.170.86/verify?email=' + email + '&key=' + user['verification']
			message = 'Subject: Verify Your Email\n\n Click here to verify your email\n' + url + '\n'
			message += 'validation key: <' + user['verification'] + '>'
			self._send_email(email, message)
			users = get_users_coll()
			users.insert(user)
			return {"status":"OK"}
		except Exception as e:
			print(e, sys.stderr)			
			return {"status":"ERROR"}
	
	def _send_email(receiver, message):
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


def parse_args_list(argnames):
	parser = reqparse.RequestParser()
	for arg in argnames:
		parser.add_argument(arg)
	args = parser.parse_args()
	return args

def get_users_coll():
	myclient = pymongo.MongoClient('mongodb://130.245.170.88:27017/')
	mydb = myclient['warmup2']
	users = mydb['users']
	return users

api.add_resource(Authenticate, '/authenticate')
api.add_resource(Verify, '/verify')
api.add_resource(ValidateNew, '/validatenew')
api.add_resource(AddUser, '/adduser')


if __name__ == '__main__':
	app.run(debug=True)