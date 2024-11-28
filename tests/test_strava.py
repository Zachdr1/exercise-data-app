import unittest
from unittest.mock import patch, MagicMock
from src.utils.strava import Strava

class TestStrava(unittest.TestCase):
    def setUp(self):
        self.mock_user = MagicMock()
        self.mock_user.access_token = "mock_access_token"
        self.mock_user.refresh_token = "mock_refresh_token"
        self.mock_user.is_token_expired.return_value = False
        self.strava = Strava(
            user=self.mock_user,
            client_id="mock_client_id",
            client_secret="mock_client_secret"
        )

    @patch('src.utils.strava.make_request')
    def test_list_activities(self, mock_make_request):
        mock_make_request.return_value = [{"id": 1, "name": "Activity 1"}]
        response = self.strava.list_activities()
        mock_make_request.assert_called_once_with(
            url=f"https://www.strava.com/api/v3/athlete/activities",
            method='GET',
            headers={"Authorization": "Bearer mock_access_token"}
        )
        self.assertEqual(response, [{"id": 1, "name": "Activity 1"}])

    @patch('src.utils.strava.make_request')
    def test_get_activity(self, mock_make_request):
        mock_make_request.return_value = {"id": 1, "name": "Activity 1"}
        response = self.strava.get_activity(1)
        mock_make_request.assert_called_once_with(
            url=f"https://www.strava.com/api/v3/activities/1",
            method='GET',
            headers={"Authorization": "Bearer mock_access_token"}
        )
        self.assertEqual(response, {"id": 1, "name": "Activity 1"})

    @patch('src.utils.strava.make_request')
    def test_refresh_tokens(self, mock_make_request):
        self.mock_user.is_token_expired.return_value = True
        mock_make_request.return_value = {
            "access_token": "new_access_token",
            "expires_at": 1234567890,
            "refresh_token": "new_refresh_token"
        }
        result = self.strava.refresh_tokens()
        mock_make_request.assert_called_once_with(
            url="https://www.strava.com/oauth/token",
            method='POST',
            data={
                "client_id": "mock_client_id",
                "client_secret": "mock_client_secret",
                "grant_type": "refresh_token",
                "refresh_token": "mock_refresh_token"
            }
        )
        self.assertTrue(result)
        self.assertEqual(self.mock_user.access_token, "new_access_token")
        self.assertEqual(self.mock_user.expires_at, 1234567890)
        self.assertEqual(self.mock_user.refresh_token, "new_refresh_token")

    @patch('src.utils.strava.make_request')
    def test_exchange_auth_code(self, mock_make_request):
        mock_make_request.return_value = {
            "access_token": "auth_code_access_token",
            "refresh_token": "auth_code_refresh_token",
            "expires_at": 1234567890,
            "athlete": {"id": 1, "username": "test_user"}
        }
        self.strava.exchange_auth_code("mock_auth_code")
        mock_make_request.assert_called_once_with(
            url="https://www.strava.com/oauth/token",
            method='POST',
            data={
                "client_id": "mock_client_id",
                "client_secret": "mock_client_secret",
                "code": "mock_auth_code",
                "grant_type": "authorization_code"
            }
        )
        self.assertEqual(self.mock_user.access_token, "auth_code_access_token")
        self.assertEqual(self.mock_user.refresh_token, "auth_code_refresh_token")
        self.assertEqual(self.mock_user.token_expires_at, 1234567890)
        self.assertEqual(self.mock_user.id, 1)
        self.assertEqual(self.mock_user.username, "test_user")

    @patch('src.utils.strava.make_request')
    def test_get_activity_streams(self, mock_make_request):
        mock_make_request.return_value = {"latlng": {"data": [[0, 0], [1, 1]]}}
        response = self.strava.get_activity_streams(1)
        mock_make_request.assert_called_once_with(
            url=f"https://www.strava.com/api/v3/activities/1/streams",
            method='GET',
            headers={"Authorization": "Bearer mock_access_token"},
            params={
                "keys": "latlng,time,altitude,velocity_smooth,time,distance,cadence",
                "key_by_type": "true"
            }
        )
        self.assertEqual(response, {"latlng": {"data": [[0, 0], [1, 1]]}})

    def test_create_gpx_from_streams(self):
        mock_stream_data = {
            "latlng": {"data": [[37.7749, -122.4194], [37.7750, -122.4195]]},
            "altitude": {"data": [5.0, 6.0]},
            "time": {"data": [0, 10]},
            "distance": {"data": [0.0, 10.0]},
            "cadence": {"data": [80, 85]}
        }
        mock_activity = {"start_date": "2023-11-27T00:00:00Z"}
        gpx_data = self.strava.create_gpx_from_streams(mock_stream_data, mock_activity)
        self.assertIn(b'<trkpt lat="37.7749" lon="-122.4194">', gpx_data)
        self.assertIn(b'<ele>5.0</ele>', gpx_data)
        self.assertIn(b'<time>2023-11-27T00:00:00+00:00</time>', gpx_data)

    @patch('src.utils.strava.make_request')
    def test_upload_gpx(self, mock_make_request):
        mock_make_request.return_value = {"id": 1}
        response = self.strava.upload_gpx(b"<gpx></gpx>")
        mock_make_request.assert_called_once_with(
            url="https://www.strava.com/api/v3/uploads",
            method='POST',
            headers={"Authorization": "Bearer mock_access_token"},
            files={
                "file": ("activity.gpx", b"<gpx></gpx>"),
                "data_type": (None, "gpx"),
                "name": (None, "Duplicated Activity")
            }
        )
        self.assertEqual(response, {"id": 1})

    @patch('src.utils.strava.make_request')
    def test_get_upload(self, mock_make_request):
        mock_make_request.return_value = {"id": 1, "status": "Your activity is ready."}
        response = self.strava.get_upload(1)
        mock_make_request.assert_called_once_with(
            url="https://www.strava.com/api/v3/uploads/1",
            method='GET',
            headers={"Authorization": "Bearer mock_access_token"}
        )
        self.assertEqual(response, {"id": 1, "status": "Your activity is ready."})

    @patch('src.utils.strava.make_request')
    def test_refresh_tokens_no_refresh_needed(self, mock_make_request):
        self.mock_user.is_token_expired.return_value = False
        result = self.strava.refresh_tokens()
        mock_make_request.assert_not_called()
        self.assertTrue(result)