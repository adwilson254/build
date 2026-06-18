    txt_rivian = gui_app.texture("icons/network.png", 56, 64)
    rivian_status = None
    try:
      rivian_status = ui_state.params.get("RivianApiStatus")
    except BaseException:
      pass

    if rivian_status:
      btn_text = rivian_status.decode('utf8') if hasattr(rivian_status, 'decode') else rivian_status
    else:
      rivian_token = None
      try:
        rivian_token = ui_state.params.get("RivianApiToken")
      except BaseException:
        pass
      rivian_token = rivian_token or ""
      btn_text = "Configured" if rivian_token else "Not set"
      
    self._rivian_login_btn = BigButton("Rivian API", btn_text, icon=txt_rivian)

    def rivian_login_callback():
      def otp_callback(otp_code: str, username: str, api):
        if otp_code:
          self._rivian_login_btn.set_value("Verifying...")
          self._rivian_login_btn.set_enabled(False)
          def auth_thread():
            import json
            try:
              res = api.validate_otp(username, otp_code)
              if res.get("success"):
                ui_state.params.put("RivianApiToken", json.dumps(res["session"]))
                ui_state.params.put("RivianApiStatus", "Configured")
                self._rivian_login_btn.set_value("Configured")
              else:
                self._rivian_login_btn.set_value("Failed")
            except Exception as e:
              print(f"OTP Error: {e}")
              self._rivian_login_btn.set_value("Failed")
            self._rivian_login_btn.set_enabled(True)
          threading.Thread(target=auth_thread, daemon=True).start()

      def password_callback(password: str, username: str):
        if password:
          self._rivian_login_btn.set_value("Authenticating...")
          self._rivian_login_btn.set_enabled(False)
          def auth_thread():
            from openpilot.selfdrive.rivian.api import RivianApi
            import json
            api = RivianApi()
            try:
              res = api.login(username, password)
              if res.get("otp_needed"):
                self._rivian_login_btn.set_value("Awaiting OTP")
                gui_app.push_widget(BigInputDialog("enter 6-digit SMS code...", "", minimum_length=6, confirm_callback=lambda otp: otp_callback(otp, username, api)))
              elif res.get("success"):
                ui_state.params.put("RivianApiToken", json.dumps(res["session"]))
                ui_state.params.put("RivianApiStatus", "Configured")
                self._rivian_login_btn.set_value("Configured")
              else:
                self._rivian_login_btn.set_value("Failed")
            except Exception as e:
              print(f"Login Error: {e}")
              self._rivian_login_btn.set_value("Failed")
            self._rivian_login_btn.set_enabled(True)
          threading.Thread(target=auth_thread, daemon=True).start()

      def username_callback(username: str):
        if username:
          pwd_dlg = BigInputDialog("enter Rivian password...", "", minimum_length=1, confirm_callback=lambda p: password_callback(p, username), password_mode=True)
          gui_app.push_widget(pwd_dlg)

      user_dlg = BigInputDialog("enter Rivian username...", "", minimum_length=1, confirm_callback=username_callback)
      gui_app.push_widget(user_dlg)

    self._rivian_login_btn.set_click_callback(rivian_login_callback)
