import signal
import os
import socket
import errno
import random
import datetime
import sys
import requests
import yaml
import json
import sqlite3
from thread import *

HOST = ''
PORT = 80
REQUEST_QUEUE_SIZE = 1024

specs = yaml.load(open("spesifikasi.yaml", "r"))
start_service = ''

def zombie_killer(signum, frame):
	while True:
		try:
			pid, status = os.waitpid(
				-1,
				os.WNOHANG
			)
		except OSError:
			return
		
		if pid == 0:
			return

def getBody(req):
	body = False
	out = ""
	
	for line in req.split("\n"):
		if(line.strip().rstrip() == ""):
			body = True
		if(body):
			out += line
				
	return out
	
def getMime(req):
	if("content-type" not in req.lower()):
		return True
	
	for line in req.split("\n"):
		if("content-type:" in line.strip().rstrip().lower()):
			if("application/json" in line.strip().rstrip().lower()):
				return True
				
	return False
	
def getAcc(req):
	if("accept" not in req.lower()):
		return True

	for line in req.split("\n"):
		if("accept" in line.strip().rstrip().lower()):
			if("*/*" in line.strip().rstrip().lower()):
				return True
			elif("application/json" in line.strip().rstrip().lower()):
				return True
				
	return False

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
	elif(file.endswith(".yaml")):
		head += 'text/x-yaml\n'
		head += '; charset=UTF-8\n'
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
	db = sqlite3.connect('data.db')
	cursor = db.execute('select * from count_table')
	data = cursor.fetchone()
	
	r = requests.get('http://172.22.0.222:5000')
	r = r.json()
	out = {}
	out["apiversion"] = specs.get('info').get('version')
	out["count"] = data[1]+1
	out["currentvisit"] = start_service
	out["response"] = "Good "+r["state"]+", "+req
	
	cursor = db.execute('update count_table set value='+str(data[1]+1)+' where id='+str(data[0]))
	db.commit()
	db.close()
	return out
	
def plusone_service(req):
	out = {}
	out["apiversion"] = specs.get('info').get('version')
	out["plusoneret"] = req
	
	return out

def threaded_service(conn):
	request = conn.recv(2048)
	request_data = bytes.decode(request)
	request_method = ''
	request_uri = ''
	request_http = ''
	request_body = ''
	header = ''
	out = ''
	parsing = True
	
	try:
		request_method = request_data.split(' ')[0]
		request_uri = request_data.split(' ')[1]
		request_http = request_data.split(' ')[2]
		request_body = getBody(request_body)
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
			out = str(random.randint(-(1 << 32), (1 << 32)))
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
			api_def = specs.get('definitions')
			checker = True
			
			if(not getAcc(request_data)):
				out = "Accept content is not json"
				out = json.dumps(api_err(out, 400), sort_keys = True, indent=4)
				header = header_maker(".json", out, 400)
				checker = False
			elif(not getMime(request_data)):
				out = "Content-type is not json"
				out = json.dumps(api_err(out, 400), sort_keys = True, indent=4)
				header = header_maker(".json", out, 400)
				checker = False
			
			#/hello
			if(req_uri == 'hello' and checker):
				if(request_method == "POST"):
					api_params = api_def.get('Request').get('required')
					if(getBody(request_data).strip().rstrip() != ""):
						api_data = json.loads(getBody(request_data))
					else:
						api_data = {}
					out = ""
					header = ""
					try:
						out = json.dumps(hello_service(api_data[api_params[0]]), sort_keys = True, indent=4)
						header = header_maker(".json", out, 200)
					except:
						out = "'request' is a required property"
						out = json.dumps(api_err(out, 400), sort_keys = True, indent=4)
						header = header_maker(".json", out, 400)
				else:
					out = "Method "+request_method+" is not allowed"
					out = json.dumps(api_err(out, 405), sort_keys = True, indent=4)
					header = header_maker(".json", out, 405)
					
			#/plusone
			elif((req_uri == "plusone" or req_uri == "plus_one") and checker):
				if(request_method == "GET"):
					try:
						api_params = int(request_uri.split('/')[3])
						out = json.dumps(plusone_service(api_params+1), sort_keys = True, indent=4)
						header = header_maker(".json", out, 200)
					except:
						out = "The requested URL was not found on the server.  If you entered the URL manually please check your spelling and try again."
						out = json.dumps(api_err(out, 404), sort_keys = True, indent=4)
						header = header_maker(".json", out, 404)
				else:
					out = "Method "+request_method+" is not allowed"
					out = json.dumps(api_err(out, 405), sort_keys = True, indent=4)
					header = header_maker(".json", out, 405)
				
			elif(req_uri == 'spesifikasi.yaml'):	
				out = yaml.load(open('spesifikasi.yaml', 'r'))
				out = yaml.dump(out, default_flow_style=False)
				header = header_maker(".yaml", out, 200)
					
	#API CONTROLLER -- END

	if(out == ''):
		out = '404 Not Found: Reason: '+request_uri+', '+request_method+'\n'
		header = header_maker('', out, 404)
	
	if(parsing):
		conn.sendall(header.encode('utf-8'))
		try:
			out = out.encode('utf-8')
		except:
			out = out
		conn.sendall(out)
	
def Main():
	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	server_socket.bind((HOST, PORT))
	server_socket.listen(REQUEST_QUEUE_SIZE)

	signal.signal(signal.SIGCHLD, zombie_killer)

	while True:
		rand_value = str(random.randint(-sys.maxsize-1, sys.maxsize))
		try:
			conn, addr = server_socket.accept()
		except IOError as e:
			code, msg = e.args
			if code == errno.EINTR:
				continue
			else:
				raise
		
		start_service = str(datetime.datetime.now())
		pid = os.fork()
		if pid == 0:
			server_socket.close()
			threaded_service(conn)
			conn.close()
			os._exit(0)
		else:
			conn.close()
	
if __name__ == '__main__':
    Main()