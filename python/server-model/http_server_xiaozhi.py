from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import search_internet
# import chat_local
import chat_local_manage
from classfy_model import Classfy
import socket
import os
import threading
import sys
os.environ['KMP_DUPLICATE_LIB_OK']='TRUE'

# os.environ["TAVILY_API_KEY"] = 'xxx'
# os.environ["OPENAI_API_KEY"] = "xxx"
# os.environ["LANGSMITH_API_KEY"] = 'xxx'
# os.environ['USER_AGENT'] = "xxx"

# 使用的不是文档里面免费的API时候可能需要更改
os.environ["OPENAI_BASE_URL"] = "https://api.chatanywhere.tech"
os.environ["LANGSMITH_TRACING"]='true'
os.environ["LANGSMITH_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"]="test"



# 192.168.188.165
data_ret = {'tool': 0, 'user_id': -1, 'result': ''}
def get_ip():
    # 获取本机所有 IP 地址
    hostname = socket.gethostname()
    ip_list = []
    # 获取IP地址信息
    addr_infos = socket.getaddrinfo(hostname, None)
    for addr in addr_infos:
        ip_list.append(addr[4][0])
    host = (ip_list[-1], 8888)
    return host


# 处理对话的服务器
class http_chat_server:
    def __init__(self):
        print("chat server init")
        print("loading model...")
        self.agent_executor = search_internet.search_Moel()
        print("loading chat local model...")
        self.chat_manage = chat_local_manage.ChatLocalManage()
        print("loading classfy model...")
        self.classfy = Classfy()
    
    def deal_with_data(self, data: str):
        d = json.loads(data.replace("'", "\""), strict=False)
        # print(d)
        print("\n\n get question:", d['messages'][0]['text'], d['messages'][0]['user_id'], '\n') # 打印一下用户的输入
        if d['messages'][0]['user_id'] == -1:
            # 新用户, 分配用户id
            user_id = self.chat_manage.get_new_user_id()
            print("new user_id: ", user_id)
        else:
            user_id = d['messages'][0]['user_id']
        data_ret['user_id'] = int(user_id)
        
        if self.classfy.classfy(d['messages'][0]['text'])[0]['label'] == 'yes':
            print("searching...")
            ret = self.agent_executor.search_func(d['messages'][0]['text'])
            # 每15个字节的长度, 设置一个换行符
            length = len(ret)
            now = 0
            while now < length:
                ret = ret[:now+12] + '\n' + ret[now+12:]
                now += 13
                length += 1
            data_ret['tool'] = 1
        else:
            print("chatting...") # 小智不需要对话模型
            ret = "无工具调用"
            data_ret['tool'] = 0
        print(ret)
        return ret
    
chat_server = http_chat_server() # 服务器对象

# 处理HTTP请求
class Resquest(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        super().__init__(request, client_address, server)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data_ret).encode())

    def do_POST(self):
        datas = self.rfile.read(int(self.headers['content-length']))
        datas = datas.decode()
        ret = chat_server.deal_with_data(datas) # 处理数据, 获取AI的回答
        # 构建返回数据
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        data_ret['result'] = ret
        self.wfile.write(json.dumps(data_ret).encode())


if __name__ == '__main__':

    try:
        host = ('192.168.31.104', 8888)
        server = HTTPServer(host, Resquest)
        print("Starting server, listen at: %s:%s" % host)
        server.serve_forever()
    except KeyboardInterrupt:
        # 结束
        print("stop")
        chat_server.chat_manage.release_all_chat_executor()
        sys.exit(0)
    except Exception as e:
        print(e)
        chat_server.chat_manage.release_all_chat_executor()
        sys.exit(0)

