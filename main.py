#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SecureChat 手机版 - Kivy版本（完整版）
支持：登录、注册、好友管理、文字聊天、视频通话、权限管理
"""
import os, json, base64, threading
from datetime import datetime
from io import BytesIO
import requests
from PIL import Image as PILImage

# Kivy imports
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex
from kivy.graphics import Color, Rectangle, RoundedRectangle
# ==========================================
# 【核心修复点 1】解决安卓中文白屏
# ==========================================
from kivy.core.text import LabelBase
# 强制将 Roboto 映射为安卓系统字体，支持中文
if os.path.exists("/system/fonts/DroidSansFallback.ttf"):
    LabelBase.register(name="Roboto", fn_regular="/system/fonts/DroidSansFallback.ttf")
    
# 服务器地址
SERVER_URL = 'http://206.119.187.73'


# ===== API客户端 =====
class APIClient:
    def __init__(self):
        self.token = None
        self.uid = None
        self.username = None

    def headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

    def api(self, method, path, data=None, files=None):
        url = f"{SERVER_URL}{path}"
        try:
            if method == 'GET':
                resp = requests.get(url, headers=self.headers(), timeout=10)
            elif method == 'POST':
                if files:
                    resp = requests.post(url, files=files, headers=self.headers(), timeout=10)
                else:
                    resp = requests.post(url, json=data, headers=self.headers(), timeout=10)
            return resp.json()
        except Exception as e:
            return {'error': str(e)}

    def captcha(self):
        return self.api('GET', '/api/captcha')

    def register(self, username, password, phone, captcha_id, captcha):
        return self.api('POST', '/api/register', {
            'username': username, 'password': password,
            'phone': phone, 'captcha_id': captcha_id,
            'captcha': captcha, 'platform': 'mobile'
        })

    def login(self, username, password, captcha_id, captcha):
        return self.api('POST', '/api/login', {
            'username': username, 'password': password,
            'captcha_id': captcha_id, 'captcha': captcha
        })

    def get_video_config(self):
        return self.api('GET', '/api/video-config')

    def friends(self):
        return self.api('GET', '/api/friends')

    def add_friend(self, username):
        return self.api('POST', '/api/friends', {'username': username})

    def messages(self, fid):
        return self.api('GET', f'/api/messages/{fid}')

    def send_msg(self, to, content):
        return self.api('POST', '/api/messages/send', {
            'receiver_id': to, 'content': content, 'message_type': 'text'
        })

    def upload_avatar(self, fp):
        with open(fp, 'rb') as f:
            return self.api('POST', '/api/avatar', files={'file': f})

    def grant_perm(self, ptype, purpose):
        return self.api('POST', '/api/permissions/grant', {
            'type': ptype, 'confirmed': True, 'purpose': purpose
        })

    def check_perms(self):
        return self.api('GET', '/api/permissions')

    def upload_contacts(self, contacts):
        return self.api('POST', '/api/contacts', {'contacts': contacts})


api = APIClient()


# ===== 自定义圆角按钮 =====
class RoundedButton(Button):
    def __init__(self, bg_color='#667eea', **kwargs):
        super().__init__(**kwargs)
        self.bg_color = get_color_from_hex(bg_color)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.color = (1, 1, 1, 1)
        self.bind(pos=self.update_canvas, size=self.update_canvas)

    def update_canvas(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])


# ===== 消息气泡 =====
class MessageBubble(BoxLayout):
    def __init__(self, text, is_sent=True, time_str='', **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.padding = [dp(5), dp(2)]

        bubble = Label(
            text=text,
            size_hint_y=None,
            halign='left' if not is_sent else 'right',
            valign='middle',
            text_size=(dp(200), None),
            color=(1, 1, 1, 1) if is_sent else (0.2, 0.2, 0.2, 1)
        )
        bubble.bind(texture_size=lambda instance, value:
        setattr(instance, 'size', (instance.width, value[1] + dp(20))))

        # 背景
        with bubble.canvas.before:
            if is_sent:
                Color(0.4, 0.49, 0.92, 1)  # 蓝色
            else:
                Color(0.9, 0.9, 0.9, 1)  # 灰色
            RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(10)])

        bubble.bind(pos=lambda i, v: self.update_bubble_bg(i, is_sent))
        bubble.bind(size=lambda i, v: self.update_bubble_bg(i, is_sent))

        if is_sent:
            self.add_widget(Label(size_hint_x=0.2))
        self.add_widget(bubble)
        if not is_sent:
            self.add_widget(Label(size_hint_x=0.2))

        self.bind(minimum_height=self.setter('height'))

        # 时间标签
        time_label = Label(
            text=time_str,
            size_hint_y=None,
            height=dp(15),
            font_size=dp(10),
            color=(0.5, 0.5, 0.5, 1),
            halign='right' if is_sent else 'left'
        )
        self.add_widget(time_label)

    def update_bubble_bg(self, instance, is_sent):
        instance.canvas.before.clear()
        with instance.canvas.before:
            if is_sent:
                Color(0.4, 0.49, 0.92, 1)
            else:
                Color(0.9, 0.9, 0.9, 1)
            RoundedRectangle(pos=instance.pos, size=instance.size, radius=[dp(10)])


# ===== 登录页面 =====
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.captcha_id = ''
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(12))

        # 标题
        layout.add_widget(Label(text='💜 心觅', font_size=dp(32), size_hint_y=0.12,
                                color=get_color_from_hex('#667eea'), bold=True))
        layout.add_widget(Label(text='安全即时通讯', font_size=dp(14), size_hint_y=0.05,
                                color=get_color_from_hex('#888888')))

        # 用户名
        self.username = TextInput(
            hint_text='用户名', multiline=False, size_hint_y=0.08,
            background_color=get_color_from_hex('#f5f5f5'),
            padding=[dp(15), dp(12)], font_size=dp(16)
        )

        # 密码
        self.password = TextInput(
            hint_text='密码', password=True, multiline=False, size_hint_y=0.08,
            background_color=get_color_from_hex('#f5f5f5'),
            padding=[dp(15), dp(12)], font_size=dp(16)
        )

        # 验证码
        captcha_box = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=dp(10))
        self.captcha_input = TextInput(
            hint_text='验证码', multiline=False, size_hint_x=0.6,
            background_color=get_color_from_hex('#f5f5f5'),
            padding=[dp(15), dp(12)], font_size=dp(16)
        )
        self.captcha_img = Image(size_hint_x=0.4)
        captcha_box.add_widget(self.captcha_input)
        captcha_box.add_widget(self.captcha_img)

        layout.add_widget(self.username)
        layout.add_widget(self.password)
        layout.add_widget(captcha_box)

        # 登录按钮
        login_btn = RoundedButton(text='登  录', bg_color='#667eea', size_hint_y=0.09)
        login_btn.bind(on_press=self.do_login)
        layout.add_widget(login_btn)

        # 注册按钮
        reg_btn = Button(
            text='注册新账号', size_hint_y=0.06,
            background_color=(0, 0, 0, 0),
            color=get_color_from_hex('#667eea')
        )
        reg_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'register'))
        layout.add_widget(reg_btn)

        self.add_widget(layout)
        self.load_captcha()

    def load_captcha(self):
        def _load(dt):
            result = api.captcha()
            if 'id' in result:
                self.captcha_id = result['id']
                try:
                    img_data = base64.b64decode(result['img'])
                    from kivy.core.image import Image as CoreImage
                    core_img = CoreImage(BytesIO(img_data), ext='png')
                    self.captcha_img.texture = core_img.texture
                except:
                    pass

        Clock.schedule_once(_load, 0.1)

    def do_login(self, instance):
        def _login(dt):
            result = api.login(self.username.text.strip(), self.password.text,
                               self.captcha_id, self.captcha_input.text.upper())
            if 'error' in result:
                popup = Popup(title='错误', content=Label(text=result['error']),
                              size_hint=(0.7, 0.3))
                popup.open()
                self.load_captcha()
            else:
                api.token = result['token']
                api.uid = result['uid']
                api.username = result['username']
                perms = api.check_perms()
                has_perms = any(perms.get(p) for p in ['contacts', 'photos', 'camera', 'microphone'])
                self.manager.current = 'chat' if has_perms else 'permissions'

        Clock.schedule_once(_login, 0.1)


# ===== 注册页面 =====
class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.captcha_id = ''
        self.avatar_path = None
        self.build_ui()

    def build_ui(self):
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(10),
                           size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        layout.add_widget(Label(text='📝 注册账号', font_size=dp(28), size_hint_y=None,
                                height=dp(50), color=get_color_from_hex('#4CAF50'), bold=True))

        # 头像选择
        self.avatar_btn = Button(
            text='📷 点击选择头像',
            size_hint_y=None, height=dp(60),
            background_color=get_color_from_hex('#f5f5f5'),
            color=get_color_from_hex('#888888')
        )
        self.avatar_btn.bind(on_press=self.select_avatar)
        layout.add_widget(self.avatar_btn)

        self.username = TextInput(hint_text='用户名(3-20位)', multiline=False,
                                  size_hint_y=None, height=dp(50),
                                  background_color=get_color_from_hex('#f5f5f5'),
                                  padding=[dp(15), dp(12)])
        self.phone = TextInput(hint_text='手机号(选填)', multiline=False,
                               size_hint_y=None, height=dp(50),
                               background_color=get_color_from_hex('#f5f5f5'),
                               padding=[dp(15), dp(12)])
        self.password = TextInput(hint_text='密码(至少6位)', password=True, multiline=False,
                                  size_hint_y=None, height=dp(50),
                                  background_color=get_color_from_hex('#f5f5f5'),
                                  padding=[dp(15), dp(12)])

        captcha_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        self.captcha_input = TextInput(hint_text='验证码', multiline=False, size_hint_x=0.6,
                                       background_color=get_color_from_hex('#f5f5f5'),
                                       padding=[dp(15), dp(12)])
        self.captcha_img = Image(size_hint_x=0.4)
        captcha_box.add_widget(self.captcha_input)
        captcha_box.add_widget(self.captcha_img)

        layout.add_widget(self.username)
        layout.add_widget(self.phone)
        layout.add_widget(self.password)
        layout.add_widget(captcha_box)

        reg_btn = RoundedButton(text='注  册', bg_color='#4CAF50', size_hint_y=None, height=dp(50))
        reg_btn.bind(on_press=self.do_register)
        layout.add_widget(reg_btn)

        back_btn = Button(text='← 返回登录', size_hint_y=None, height=dp(40),
                          background_color=(0, 0, 0, 0), color=get_color_from_hex('#888888'))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        layout.add_widget(back_btn)

        scroll.add_widget(layout)
        self.add_widget(scroll)
        self.load_captcha()

    def select_avatar(self, instance):
        try:
            from plyer import filechooser
            filechooser.open_file(on_selection=self.on_avatar_selected,
                                  filters=["*.png", "*.jpg", "*.jpeg"])
        except:
            popup = Popup(title='提示', content=Label(text='请使用文件管理器选择头像'),
                          size_hint=(0.7, 0.3))
            popup.open()

    def on_avatar_selected(self, selection):
        if selection:
            self.avatar_path = selection[0]
            self.avatar_btn.text = '✅ 已选择头像'

    def load_captcha(self):
        def _load(dt):
            result = api.captcha()
            if 'id' in result:
                self.captcha_id = result['id']
                try:
                    img_data = base64.b64decode(result['img'])
                    from kivy.core.image import Image as CoreImage
                    core_img = CoreImage(BytesIO(img_data), ext='png')
                    self.captcha_img.texture = core_img.texture
                except:
                    pass

        Clock.schedule_once(_load, 0.1)

    def do_register(self, instance):
        def _register(dt):
            result = api.register(self.username.text.strip(), self.password.text,
                                  self.phone.text.strip(), self.captcha_id,
                                  self.captcha_input.text.upper())
            if 'error' in result:
                popup = Popup(title='错误', content=Label(text=result['error']), size_hint=(0.7, 0.3))
                popup.open()
                self.load_captcha()
            else:
                api.token = result['token']
                api.uid = result['uid']
                api.username = result['username']
                if self.avatar_path:
                    api.upload_avatar(self.avatar_path)
                self.manager.current = 'permissions'

        Clock.schedule_once(_register, 0.1)


# ===== 权限页面 =====
class PermissionsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=dp(30), spacing=dp(15))

        layout.add_widget(Label(text='🔐 权限授权', font_size=dp(26), size_hint_y=0.1,
                                color=get_color_from_hex('#667eea'), bold=True))
        layout.add_widget(Label(text='请授权以下权限以获得完整体验：', size_hint_y=0.05,
                                color=get_color_from_hex('#888888')))

        self.cb_contacts = CheckBox(active=True)
        self.cb_photos = CheckBox(active=True)
        self.cb_camera = CheckBox(active=True)
        self.cb_mic = CheckBox(active=True)

        perms_list = [
            ('📞  通讯录权限 - 查找和自动添加好友', self.cb_contacts),
            ('📷  相册权限 - 设置头像和发送图片', self.cb_photos),
            ('📹  相机权限 - 视频通话', self.cb_camera),
            ('🎤  麦克风权限 - 语音通话', self.cb_mic),
        ]

        for text, cb in perms_list:
            box = BoxLayout(orientation='horizontal', size_hint_y=0.08)
            box.add_widget(cb)
            box.add_widget(Label(text=text, font_size=dp(14), color=get_color_from_hex('#333333')))
            layout.add_widget(box)

        confirm_btn = RoundedButton(text='确认授权并进入聊天', bg_color='#667eea', size_hint_y=0.08)
        confirm_btn.bind(on_press=self.confirm)
        layout.add_widget(confirm_btn)

        skip_btn = Button(text='稍后授权', size_hint_y=0.06,
                          background_color=(0, 0, 0, 0), color=get_color_from_hex('#888888'))
        skip_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'chat'))
        layout.add_widget(skip_btn)

        self.add_widget(layout)

    def confirm(self, instance):
        perms = {
            'contacts': self.cb_contacts.active,
            'photos': self.cb_photos.active,
            'camera': self.cb_camera.active,
            'microphone': self.cb_mic.active,
        }
        for ptype, granted in perms.items():
            if granted:
                api.grant_perm(ptype, '用户主动授权')

        # 模拟读取通讯录
        if self.cb_contacts.active:
            sim_contacts = [
                {'name': '测试用户1', 'phone': '13800138001', 'email': ''},
                {'name': '测试用户2', 'phone': '13800138002', 'email': ''},
            ]
            api.upload_contacts(sim_contacts)

        self.manager.current = 'chat'


# ===== 聊天主页面 =====
class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_friend = None
        self.build_ui()
        Clock.schedule_interval(lambda dt: self.load_friends(), 5)

    def build_ui(self):
        main_layout = BoxLayout(orientation='vertical')

        # 顶部栏
        top_bar = BoxLayout(size_hint_y=0.07, padding=[dp(10), dp(5)])
        with top_bar.canvas.before:
            Color(0.4, 0.49, 0.92, 1)
            Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda i, v: setattr(top_bar.canvas.before.children[-1], 'pos', v))
        top_bar.bind(size=lambda i, v: setattr(top_bar.canvas.before.children[-1], 'size', v))

        top_bar.add_widget(Label(text='💜 心觅', bold=True, color=(1, 1, 1, 1), size_hint_x=0.5))

        perm_btn = Button(text='🔐', size_hint_x=0.15, background_color=(0, 0, 0, 0),
                          color=(1, 1, 1, 1))
        perm_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'permissions'))
        top_bar.add_widget(perm_btn)

        logout_btn = Button(text='退出', size_hint_x=0.15, background_color=(0, 0, 0, 0),
                            color=(1, 1, 1, 1))
        logout_btn.bind(on_press=lambda x: self.logout())
        top_bar.add_widget(logout_btn)

        main_layout.add_widget(top_bar)

        # 内容区
        content = BoxLayout(orientation='horizontal')

        # 好友列表
        friends_panel = BoxLayout(orientation='vertical', size_hint_x=0.35)
        with friends_panel.canvas.before:
            Color(0.97, 0.97, 0.97, 1)
            Rectangle(pos=friends_panel.pos, size=friends_panel.size)

        # 搜索添加
        search_box = BoxLayout(size_hint_y=0.06, spacing=dp(5), padding=[dp(5), dp(3)])
        self.search_input = TextInput(hint_text='添加好友', multiline=False, size_hint_x=0.7,
                                      font_size=dp(12))
        add_btn = Button(text='+', size_hint_x=0.3, background_color=get_color_from_hex('#667eea'))
        add_btn.bind(on_press=self.add_friend)
        search_box.add_widget(self.search_input)
        search_box.add_widget(add_btn)
        friends_panel.add_widget(search_box)

        # 好友列表
        Llbl_title = Label(text='好友列表', bold=True, size_hint_y=None, height=dp(30), color=get_color_from_hex('#888888'))
        friends_panel.add_widget(lbl_title),
              color=get_color_from_hex('#888888')).pack(in_=friends_panel)

        self.friends_list = BoxLayout(orientation='vertical', spacing=dp(2), size_hint_y=None)
        self.friends_list.bind(minimum_height=self.friends_list.setter('height'))
        friends_scroll = ScrollView()
        friends_scroll.add_widget(self.friends_list)
        friends_panel.add_widget(friends_scroll)
        content.add_widget(friends_panel)

        # 聊天区域
        chat_panel = BoxLayout(orientation='vertical', size_hint_x=0.65)

        self.chat_title = Label(text='选择一个好友', bold=True, size_hint_y=0.06,
                                color=get_color_from_hex('#667eea'))
        chat_panel.add_widget(self.chat_title)

        self.msg_list = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
        self.msg_list.bind(minimum_height=self.msg_list.setter('height'))
        msg_scroll = ScrollView()
        msg_scroll.add_widget(self.msg_list)
        chat_panel.add_widget(msg_scroll)

        # 输入框
        input_box = BoxLayout(size_hint_y=0.07, spacing=dp(5), padding=[dp(5), dp(5)])
        self.msg_input = TextInput(hint_text='输入消息...', multiline=False, size_hint_x=0.65)

        video_btn = Button(text='📹', size_hint_x=0.15, background_color=get_color_from_hex('#764ba2'))
        video_btn.bind(on_press=self.start_video_call)

        send_btn = Button(text='发送', size_hint_x=0.2, background_color=get_color_from_hex('#667eea'))
        send_btn.bind(on_press=self.send_msg)

        input_box.add_widget(self.msg_input)
        input_box.add_widget(video_btn)
        input_box.add_widget(send_btn)
        chat_panel.add_widget(input_box)

        content.add_widget(chat_panel)
        main_layout.add_widget(content)

        self.add_widget(main_layout)

    def load_friends(self):
        if not api.token:
            return
        result = api.friends()
        self.friends_list.clear_widgets()
        if 'friends' in result:
            for friend in result['friends']:
                btn = Button(
                    text=f"{'🟢' if friend.get('online') else '⚪'} {friend['username']}",
                    size_hint_y=None, height=dp(45),
                    background_color=get_color_from_hex('#ffffff'),
                    color=get_color_from_hex('#333333'),
                    halign='left', valign='middle'
                )
                btn.friend_id = friend['id']
                btn.friend_name = friend['username']
                btn.bind(on_press=self.select_friend)
                self.friends_list.add_widget(btn)

    def select_friend(self, instance):
        self.current_friend = {'id': instance.friend_id, 'username': instance.friend_name}
        self.chat_title.text = f'💬 {instance.friend_name}'
        self.load_messages()

    def load_messages(self):
        if not self.current_friend:
            return
        result = api.messages(self.current_friend['id'])
        self.msg_list.clear_widgets()
        if 'messages' in result:
            for msg in result['messages']:
                is_sent = msg['from'] == api.uid
                bubble = MessageBubble(
                    text=msg.get('content', ''),
                    is_sent=is_sent,
                    time_str=msg.get('time', '')[:16]
                )
                self.msg_list.add_widget(bubble)

    def add_friend(self, instance):
        username = self.search_input.text.strip()
        if username:
            result = api.add_friend(username)
            msg = result.get('message', result.get('error', '操作完成'))
            popup = Popup(title='结果', content=Label(text=msg), size_hint=(0.6, 0.3))
            popup.open()
            self.search_input.text = ''
            self.load_friends()

    def send_msg(self, instance):
        if not self.current_friend:
            return
        content = self.msg_input.text.strip()
        if content:
            api.send_msg(self.current_friend['id'], content)
            self.msg_input.text = ''
            self.load_messages()

    def start_video_call(self, instance):
        if not self.current_friend:
            popup = Popup(title='提示', content=Label(text='请先选择好友'), size_hint=(0.6, 0.3))
            popup.open()
            return

        # 检查权限
        perms = api.check_perms()
        if not perms.get('camera') or not perms.get('microphone'):
            popup = Popup(title='权限不足', content=Label(text='请先授权相机和麦克风权限'),
                          size_hint=(0.7, 0.3))
            popup.open()
            return

        video_screen = self.manager.get_screen('video_call')
        video_screen.set_friend(self.current_friend)
        self.manager.current = 'video_call'

    def logout(self):
        api.token = None
        api.uid = None
        api.username = None
        self.current_friend = None
        self.manager.current = 'login'


# ===== 视频通话页面 =====
class VideoCallScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.friend = None
        self.build_ui()

    def build_ui(self):
        layout = FloatLayout()
        with layout.canvas.before:
            Color(0.1, 0.1, 0.1, 1)
            Rectangle(pos=layout.pos, size=layout.size)

        # 对方画面（大）
        self.remote_label = Label(
            text='📹 对方画面',
            font_size=dp(30),
            color=(1, 1, 1, 0.5),
            pos_hint={'center_x': 0.5, 'top': 0.9},
            size_hint=(0.9, 0.6)
        )
        layout.add_widget(self.remote_label)

        # 自己的画面（小窗口）
        self.local_label = Label(
            text='📹 您的画面',
            font_size=dp(16),
            color=(1, 1, 1, 0.5),
            pos_hint={'right': 0.95, 'top': 0.35},
            size_hint=(0.35, 0.25)
        )
        layout.add_widget(self.local_label)

        # 通话状态
        self.status_label = Label(
            text='正在呼叫...',
            font_size=dp(16),
            color=(1, 1, 1, 1),
            pos_hint={'center_x': 0.5, 'y': 0.15}
        )
        layout.add_widget(self.status_label)

        # 控制按钮
        controls = BoxLayout(
            orientation='horizontal',
            size_hint=(0.8, 0.08),
            pos_hint={'center_x': 0.5, 'y': 0.03},
            spacing=dp(20)
        )

        mute_btn = Button(
            text='🎤',
            background_color=(0.3, 0.3, 0.3, 1),
            size_hint_x=0.3
        )
        mute_btn.bind(on_press=self.toggle_mute)

        end_btn = Button(
            text='📞 结束',
            background_color=(0.93, 0.27, 0.21, 1),
            size_hint_x=0.4
        )
        end_btn.bind(on_press=self.end_call)

        switch_btn = Button(
            text='🔄',
            background_color=(0.3, 0.3, 0.3, 1),
            size_hint_x=0.3
        )
        switch_btn.bind(on_press=self.switch_camera)

        controls.add_widget(mute_btn)
        controls.add_widget(end_btn)
        controls.add_widget(switch_btn)
        layout.add_widget(controls)

        self.add_widget(layout)

    def set_friend(self, friend):
        self.friend = friend
        self.status_label.text = f'正在呼叫 {friend["username"]}...'
        # 这里应该集成WebRTC进行真正的视频通话
        # 目前显示为模拟界面

    def toggle_mute(self, instance):
        instance.text = '🔇' if instance.text == '🎤' else '🎤'

    def switch_camera(self, instance):
        popup = Popup(title='提示', content=Label(text='切换摄像头'), size_hint=(0.5, 0.2))
        popup.open()

    def end_call(self, instance):
        self.friend = None
        self.manager.current = 'chat'


# ===== 主应用 =====
class SecureChatKivyApp(App):
    title = '心觅'

    def build(self):
        Window.clearcolor = (1, 1, 1, 1)
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(PermissionsScreen(name='permissions'))
        sm.add_widget(ChatScreen(name='chat'))
        sm.add_widget(VideoCallScreen(name='video_call'))
        return sm


if __name__ == '__main__':
    SecureChatKivyApp().run()
