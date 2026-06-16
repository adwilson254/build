import uuid
import requests
from openpilot.common.swaglog import cloudlog

class RivianAPIError(Exception): pass
class RivianAuthError(RivianAPIError): pass
class RivianNetworkError(RivianAPIError): pass

GRAPHQL_GATEWAY = "https://rivian.com/api/gql/gateway/graphql"
APOLLO_CLIENT_NAME = "com.rivian.ios.consumer-apollo-ios"

def _get_base_headers():
    return {
        "User-Agent": "RivianApp/707 CFNetwork/1237 Darwin/20.4.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Apollographql-Client-Name": APOLLO_CLIENT_NAME,
        "dc-cid": f"m-ios-{uuid.uuid4()}"
    }

class RivianApi:
    """
    Client class for interacting with the official Rivian GraphQL API.
    Handles session management, CSRF token creation, MFA/OTP authentication,
    and querying the current vehicle telemetry/state.
    """
    def __init__(self, session_data=None):
        self.session_data = session_data or {}

    def get_headers(self, require_auth=True):
        """
        Constructs the HTTP headers required for Rivian API requests.
        Injects CSRF and App/User session tokens dynamically based on the current
        authentication state.
        
        Args:
            require_auth (bool): If True, requires full User Session token (U-Sess)
                                 and Bearer Access Token. False during login/OTP.
        """
        headers = _get_base_headers()
        if "csrf_token" in self.session_data:
            headers["Csrf-Token"] = self.session_data["csrf_token"]
        if "app_session_token" in self.session_data:
            headers["A-Sess"] = self.session_data["app_session_token"]

        if require_auth:
            if "user_session_token" in self.session_data:
                headers["U-Sess"] = self.session_data["user_session_token"]
            if "access_token" in self.session_data:
                headers["Authorization"] = f"Bearer {self.session_data['access_token']}"
        return headers

    def _create_csrf_token(self):
        graphql_json = {
            "operationName": "CreateCSRFToken",
            "query": "mutation CreateCSRFToken {\n  createCsrfToken {\n    __typename\n    csrfToken\n    appSessionToken\n  }\n}",
            "variables": None,
        }
        resp = requests.post(GRAPHQL_GATEWAY, headers=_get_base_headers(), json=graphql_json, timeout=10)
        if resp.status_code != 200:
            cloudlog.error(f"Rivian API Error Response: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RivianAPIError(f"GraphQL Error: {data['errors']}")

        csrf_data = data["data"]["createCsrfToken"]
        self.session_data["csrf_token"] = csrf_data["csrfToken"]
        self.session_data["app_session_token"] = csrf_data["appSessionToken"]

    def login(self, username, password):
        """
        Initiates the login process using email and password.
        
        If the account has 2FA/MFA enabled, this will return `{"otp_needed": True}`
        and prompt the user to validate the OTP in the next step. Otherwise,
        it retrieves full access and refresh tokens.
        """
        self._create_csrf_token()
        graphql_json = {
            "operationName": "Login",
            "query": "mutation Login($email: String!, $password: String!) {\n  login(email: $email, password: $password) {\n    __typename\n    ... on MobileLoginResponse {\n      __typename\n      accessToken\n      refreshToken\n      userSessionToken\n    }\n    ... on MobileMFALoginResponse {\n      __typename\n      otpToken\n    }\n  }\n}",
            "variables": {"email": username, "password": password},
        }
        resp = requests.post(GRAPHQL_GATEWAY, headers=self.get_headers(require_auth=False), json=graphql_json, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RivianAPIError(f"Login Error: {data['errors']}")

        login_data = data["data"]["login"]
        if "otpToken" in login_data:
            self.session_data["otp_token"] = login_data["otpToken"]
            return {"otp_needed": True}
        else:
            self.session_data["access_token"] = login_data["accessToken"]
            self.session_data["refresh_token"] = login_data["refreshToken"]
            self.session_data["user_session_token"] = login_data["userSessionToken"]
            return {"success": True, "session": self.session_data}

    def validate_otp(self, username, otp_code):
        graphql_json = {
            "operationName": "LoginWithOTP",
            "query": "mutation LoginWithOTP($email: String!, $otpCode: String!, $otpToken: String!) {\n  loginWithOTP(email: $email, otpCode: $otpCode, otpToken: $otpToken) {\n    __typename\n    ... on MobileLoginResponse {\n      __typename\n      accessToken\n      refreshToken\n      userSessionToken\n    }\n  }\n}",
            "variables": {
                "email": username,
                "otpCode": otp_code,
                "otpToken": self.session_data.get("otp_token", ""),
            },
        }
        resp = requests.post(GRAPHQL_GATEWAY, headers=self.get_headers(require_auth=False), json=graphql_json, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RivianAPIError(f"OTP Error: {data['errors']}")

        login_data = data["data"]["loginWithOTP"]
        self.session_data["access_token"] = login_data["accessToken"]
        self.session_data["refresh_token"] = login_data["refreshToken"]
        self.session_data["user_session_token"] = login_data["userSessionToken"]
        return {"success": True, "session": self.session_data}

    def get_user_info(self):
        graphql_json = {
            "operationName": "getUserInfo",
            "query": "query getUserInfo { currentUser { __typename id vehicles { id vin name } } }",
            "variables": None,
        }
        resp = requests.post(GRAPHQL_GATEWAY, headers=self.get_headers(require_auth=True), json=graphql_json, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            if any(e.get("extensions", {}).get("code") == "UNAUTHENTICATED" for e in data["errors"]):
                return {"unauthenticated": True}
            raise RivianAPIError(f"User Info Error: {data['errors']}")
        return data

    def get_vehicle_state(self, vehicle_id):
        """
        Executes a targeted GraphQL query to fetch the absolute latest telemetry 
        data (battery, doors, temperature, location, software version) for a given vehicle.
        
        Args:
            vehicle_id (str): The specific Rivian ID to query.
        Returns:
            dict: Raw telemetry dictionary mapped exactly to the queried fields.
        """
        # targeted bug-free query
        query = """
        query GetVehicleState($vehicleID: String!) {
            vehicleState(id: $vehicleID) {
                gnssLocation { latitude longitude timeStamp }
                gnssSpeed { timeStamp value }
                gnssAltitude { timeStamp value }
                gnssError { timeStamp positionVertical positionHorizontal speed bearing }
                alarmSoundStatus { timeStamp value }
                timeToEndOfCharge { timeStamp value }
                doorFrontLeftLocked { timeStamp value }
                doorFrontLeftClosed { timeStamp value }
                doorFrontRightLocked { timeStamp value }
                doorFrontRightClosed { timeStamp value }
                doorRearLeftLocked { timeStamp value }
                doorRearLeftClosed { timeStamp value }
                doorRearRightLocked { timeStamp value }
                doorRearRightClosed { timeStamp value }
                windowFrontLeftClosed { timeStamp value }
                windowFrontRightClosed { timeStamp value }
                windowFrontLeftCalibrated { timeStamp value }
                windowFrontRightCalibrated { timeStamp value }
                windowRearLeftCalibrated { timeStamp value }
                windowRearRightCalibrated { timeStamp value }
                closureFrunkLocked { timeStamp value }
                closureFrunkClosed { timeStamp value }
                gearGuardLocked { timeStamp value }
                closureLiftgateLocked { timeStamp value }
                closureLiftgateClosed { timeStamp value }
                windowRearLeftClosed { timeStamp value }
                windowRearRightClosed { timeStamp value }
                closureSideBinLeftLocked { timeStamp value }
                closureSideBinLeftClosed { timeStamp value }
                closureSideBinRightLocked { timeStamp value }
                closureSideBinRightClosed { timeStamp value }
                closureTailgateLocked { timeStamp value }
                closureTailgateClosed { timeStamp value }
                closureTonneauLocked { timeStamp value }
                closureTonneauClosed { timeStamp value }
                wiperFluidState { timeStamp value }
                powerState { timeStamp value }
                batteryHvThermalEventPropagation { timeStamp value }
                vehicleMileage { timeStamp value }
                brakeFluidLow { timeStamp value }
                gearStatus { timeStamp value }
                tirePressureStatusFrontLeft { timeStamp value }
                tirePressureStatusValidFrontLeft { timeStamp value }
                tirePressureStatusFrontRight { timeStamp value }
                tirePressureStatusValidFrontRight { timeStamp value }
                tirePressureStatusRearLeft { timeStamp value }
                tirePressureStatusValidRearLeft { timeStamp value }
                tirePressureStatusRearRight { timeStamp value }
                tirePressureStatusValidRearRight { timeStamp value }
                batteryLevel { timeStamp value }
                chargerState { timeStamp value }
                batteryLimit { timeStamp value }
                remoteChargingAvailable { timeStamp value }
                batteryHvThermalEvent { timeStamp value }
                rangeThreshold { timeStamp value }
                distanceToEmpty { timeStamp value }
                otaAvailableVersionNumber { timeStamp value }
                otaAvailableVersionWeek { timeStamp value }
                otaAvailableVersionYear { timeStamp value }
                otaCurrentVersionNumber { timeStamp value }
                otaCurrentVersionWeek { timeStamp value }
                otaCurrentVersionYear { timeStamp value }
                otaDownloadProgress { timeStamp value }
                otaInstallDuration { timeStamp value }
                otaInstallProgress { timeStamp value }
                otaInstallReady { timeStamp value }
                otaInstallTime { timeStamp value }
                otaInstallType { timeStamp value }
                otaStatus { timeStamp value }
                otaCurrentStatus { timeStamp value }
                cabinClimateInteriorTemperature { timeStamp value }
                cabinPreconditioningStatus { timeStamp value }
                cabinPreconditioningType { timeStamp value }
                petModeStatus { timeStamp value }
                petModeTemperatureStatus { timeStamp value }
                cabinClimateDriverTemperature { timeStamp value }
                gearGuardVideoStatus { timeStamp value }
                gearGuardVideoMode { timeStamp value }
                gearGuardVideoTermsAccepted { timeStamp value }
                defrostDefogStatus { timeStamp value }
                steeringWheelHeat { timeStamp value }
                seatFrontLeftHeat { timeStamp value }
                seatFrontRightHeat { timeStamp value }
                seatRearLeftHeat { timeStamp value }
                seatRearRightHeat { timeStamp value }
                chargerStatus { timeStamp value }
                seatFrontLeftVent { timeStamp value }
                seatFrontRightVent { timeStamp value }
                chargerDerateStatus { timeStamp value }
                driveMode { timeStamp value }
                batteryCapacity { timeStamp value }
            }
        }
        """
        graphql_json = {
            "operationName": "GetVehicleState",
            "query": query,
            "variables": {"vehicleID": vehicle_id}
        }
        resp = requests.post(GRAPHQL_GATEWAY, headers=self.get_headers(require_auth=True), json=graphql_json, timeout=10)
        if resp.status_code != 200:
            cloudlog.error(f"Rivian API Error Response: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            if any(e.get("extensions", {}).get("code") == "UNAUTHENTICATED" for e in data["errors"]):
                return {"unauthenticated": True}
            raise RivianAPIError(f"Vehicle State Error: {data['errors']}")
        return data
