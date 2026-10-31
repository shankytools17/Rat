[app]
title = My Kivy App
package.name = mykivyapp
package.domain = org.example
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,json,txt,ttf,mp3,wav
version = 0.1
requirements = python3,kivy,cryptography,websockets
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a
android.api = 35
android.minapi = 24
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
