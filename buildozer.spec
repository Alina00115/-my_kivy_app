[app]

# (str) Title of your application
title = My Application

# (str) Package name
package.name = myapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, venv

# (list) List of exclusions using pattern matching
source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
# 精准锁死编译所需的 Python 环境，并为 KivyMD/Pillow 补全了核心图像支持库
requirements = python3==3.10.12,hostpython3==3.10.12,kivy,kivymd,pillow,jpeg,png

# (list) Supported orientations
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# =========================================================
# Android specific configurations (无视高级工具，强行锁死稳定版)
# =========================================================

# (string) Presplash background color
android.presplash_color = #FFFFFF

# (list) Permissions
android.permissions = android.permission.INTERNET

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use (完美解封)
android.ndk = 25b

# (int) Android NDK API to use
android.ndk_api = 21

# (str) Android Build Tools version to use (解决 aidl 报错、找不到路径的终极关键)
android.build_tools_version = 33.0.2

# (list) The Android architectures to build for (专为现代安卓手机编译的 64 位架构)
android.archs = arm64-v8a

# (bool) Enable AndroidX support.
android.enable_androidx = True

# (bool) If True, then automatically accept SDK license agreements.
android.accept_sdk_license = True
