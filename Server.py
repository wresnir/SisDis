import socket
import random
import datetime
import sys
import requests
import yaml
import json
from _thread import *


#host = '172.22.0.203'
host = ''
port = 80
server_socket =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)

specs = yaml.load(open("spesifikasi.yaml", "r"))
r = '{"state": "Morning", "datetime": "2018-10-07 09:34:19"}'
r = json.loads(r)




try:
	server_socket.bind((host,port))
except:
	print("Binding Fail at "+host+":"+str(port))
	
server_socket.listen(5)

def code_handler(code):
	head = ''
	if(code == 200):
		head = 'HTTP/1.1 200 OK\n'
	elif(code == 302):
		head = 'HTTP/1.1 302 FOUND\n'
	elif(code == 400):
		head = 'HTTP/1.1 400 BAD REQUEST\n'
	elif(code == 404):
		head = 'HTTP/1.1 404 NOT FOUND\n'
	elif(code == 405):
		head = 'HTTP/1.1 405 METHOD NOT ALLOWED\n'
	elif(code == 500):
		head = 'HTTP/1.1 500 INTERNAL SERVER ERROR\n'
	elif(code == 501):
		head = 'HTTP/1.1 501 NOT IMPLEMENTED\n'
		
	head += 'Connection: close\n'
	return head
	
def api_err(detail, code):
	out = {}
	out["detail"] = detail
	if(code == 200):
		out["status"] = 200
		out["title"] = "Ok"
	elif(code == 302):
		out["status"] = 302
		out["title"] = "Found"
	elif(code == 400):
		out["status"] = 400
		out["title"] = "Bad request"
	elif(code == 404):
		out["status"] = 404
		out["title"] = "Not found"
	elif(code == 405):
		out["status"] = 405
		out["title"] = "Method not allowed"
	elif(code == 500):
		out["status"] = 500
		out["title"] = "Internal server error"
	elif(code == 501):
		out["status"] = 501
		out["title"] = "Not implemented"
		
	return out
	
def mimetype_handler(file):
	head = 'Content-Type: '
	if(file.endswith(".jpg")):
		head += 'image/jpg'
	elif(file.endswith(".css")):
		head += 'text/css'
		head += '; charset=UTF-8\n'
	elif(file.endswith(".html")):
		head += 'text/html'
		head += '; charset=UTF-8\n'
	elif(file.endswith(".json")):
		head += 'application/json\n'
	else:
		head += 'text/plain'
		head += '; charset=UTF-8\n'
	
	return head
	
def len_handler(file):
	head = 'Content-Length: '+str(len(file))+'\n'
	return head
	
def header_maker(type, file, code):
	header = code_handler(code)
	header += mimetype_handler(type)
	header += len_handler(file)
	header += '\n'
	return header
	
def header_maker_redirect(file, code, uri):
	header = code_handler(code)
	header += 'Location: '+uri+'\n'
	header += mimetype_handler(file)
	header += len_handler(file)
	header += '\n'
	return header
	
def hello_service(req):
	r = requests.get('http://172.22.0.222:5000')
	r = json.load(r)
	out = {}
	out["apiversion"] = specs.get('info').get('version')
	out["count"] = 1
	out["currentvisit"] = start_service
	out["resposne"] = "Good "+r["state"]+", "+req
	
	return out

def threaded_service(conn):
	start_service = str(datetime.datetime.now())
	while True:
		request = conn.recv(2048)
		request_data = bytes.decode(request)
		request_method = ''
		request_uri = ''
		request_http = ''
		header = ''
		out = ''
		parsing = True
		
		try:
			request_method = request_data.split(' ')[0]
			request_uri = request_data.split(' ')[1]
			request_http = request_data.split(' ')[2]
		except:
			parsing = False
		
		if('HTTP/1.0' not in request_http and 'HTTP/1.1' not in request_http):
			out = '400 Bad request\n'
			header = header_maker("", out, 400)
			
		elif(request_method != 'GET' and request_method != 'POST'):
			out = '501 Not Implemented: Reason: '+request_method+'\n'
			header = header_maker("", out, 501)
			
		#CONTROLLER
		elif(request_uri == '/'):
			redirect_uri = '/hello-world'
			out = '302 Found: Location: '+redirect_uri+'\n'
			header = header_maker_redirect(out, 302, redirect_uri)
			
		elif(request_uri == '/hello-world'):
		
			out = open('hello-world.html', 'r')
			out = out.read()
			if(request_method == 'GET'):
				out = out.replace('__HELLO__', "World")
				header = header_maker('.html', out, 200)
			else:
				if('x-www-form-urlencoded' in request_data):
					try:
						name = request_data.split('\n')[-1].split('=')[1]
						if('%20' in name):
							name = name.replace('%20', ' ')
						else:
							name = name.replace('+', ' ')
						out = out.replace('__HELLO__', name)
						header = header_maker('.html', out, 200)
					except:
						out = '500 Internal Server Error'
						header = header_maker('', out, 500)
				else:
					out = '400 Bad Request'
					header = header_maker('', out, 400)
				
			
		elif(request_uri == '/style'):
			out = open('style.css', 'r')
			out = out.read()
			header = header_maker('.css', out, 200)
			
		elif(request_uri == '/background'):
			out = open('background.jpg', 'rb')
			out = out.read()
			header = header_maker('.jpg', out, 200)
		
		elif(request_uri == '/info'):
			out = '400 Bad Request'
			header = header_maker('', out, 400)
		
		elif(request_uri.split('?')[0] == '/info'):
			request_uri_type = request_uri.split('?')[1]
			if(request_uri_type == 'type=random'):
				out = str(random.randint(-sys.maxsize-1, sys.maxsize))
			elif(request_uri_type == 'type=time'):
				out = str(datetime.datetime.now())
			elif('type' in request_uri_type):
				out = 'No Data'
			header = header_maker('', out, 200)
		
		#CONTROLLER -- END
		
		#API CONTROLLER
		elif('/api' in request_uri):
			if(request_uri == '/api'):
				out = '400 Bad Request'
				header = header_maker('', out, 400)
			else:
				req_uri = request_uri.split('/')[2]
				api_path = specs.get('paths').get('/'+req_uri)
				if(api_path == None):
					out = '404 Not Found'
					header = header_maker('', out, 404)
				else:
					api_def = specs.get('definitions')
					
					#/hello
					if(req_uri == 'hello'):
						if(request_method == "POST"):
							api_params = api_def.get('Request').get('required')
							api_data = json.loads(request_data.split('\n')[-1])
							out = ""
							header = ""
							try:
								out = json.dumps(hello_service(api_data[api_params[0]]))
								header = header_maker(".json", out, 200)
							except:
								err_cause = "'request' is a required property"
								out = json.dumps(api_err(err_cause, 400))
								header = header_maker(".json", out, 400)
					#/plusone
					#elif(api_path == 'plusone'):
					
					
						# TODO
						# 1. Parameter Checking
						# 2. Implement api function if pass
					
		#API CONTROLLER -- END

		
		if(out == ''):
			out = '404 Not Found: Reason: '+request_uri+', '+request_method+'\n'
			header = header_maker('', out, 404)
		
		if(parsing):
			conn.send(header.encode('utf-8'))
			try:
				out = out.encode('utf-8')
			except:
				out = out
			conn.send(out)
			
	conn.close()

while True:
	conn, addr = server_socket.accept()
	start_new_thread(threaded_service, (conn,))
	
		
	
	
	
	
