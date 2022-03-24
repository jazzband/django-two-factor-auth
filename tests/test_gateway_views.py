from django.test import RequestFactory, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from two_factor.gateways.twilio.views import TwilioCallApp


class TwilioCallAppTest(TestCase):
    @override_settings(
        TWILIO_ACCOUNT_SID="SID", TWILIO_AUTH_TOKEN="TOKEN", TWILIO_CALLER_ID="+456",
    )
    def test_get_prompt_context(self):
        factory = RequestFactory()
        request = factory.post(
            reverse("two_factor_twilio:call_app", kwargs={"token": "234567654"})
        )
        view = TwilioCallApp()
        view.request = request
        view.kwargs = {"token": "234567654"}
        self.assertEqual(
            view.get_prompt_context(),
            {"site_name": "testserver", "token": "2. 3. 4. 5. 6. 7. 6. 5. 4"},
        )
        with override_settings(TWILIO_SEPARATOR="**"):
            self.assertEqual(
                view.get_prompt_context(),
                {"site_name": "testserver", "token": "2**3**4**5**6**7**6**5**4"},
            )
