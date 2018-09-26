from django.test import TestCase

from two_factor.templatetags.device_format import agent_format


class DeviceTemplateFilterTest(TestCase):
    def test_ie(self):
        self.assertEqual(
            'Internet Explorer on Windows XP',
            agent_format('Mozilla/4.0 (Windows; MSIE 6.0; Windows NT 5.1; SV1; '
                   '.NET CLR 2.0.50727)')
        )
        self.assertEqual(
            'Internet Explorer on Windows Vista',
            agent_format('Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.0; '
                   'Trident/4.0; SLCC1; .NET CLR 2.0.50727; .NET CLR 1.1.4322;'
                   ' InfoPath.2; .NET CLR 3.5.21022; .NET CLR 3.5.30729; '
                   'MS-RTC LM 8; OfficeLiveConnector.1.4; OfficeLivePatch.1.3;'
                   ' .NET CLR 3.0.30729)')
        )
        self.assertEqual(
            'Internet Explorer on Windows 7',
            agent_format('Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; '
                   'Trident/6.0)')
        )
        self.assertEqual(
            'Internet Explorer on Windows 8',
            agent_format('Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; '
                   'Win64; x64; Trident/6.0)')
        )
        self.assertEqual(
            'Internet Explorer on Windows 8.1',
            agent_format('Mozilla/5.0 (IE 11.0; Windows NT 6.3; Trident/7.0; '
                   '.NET4.0E; .NET4.0C; rv:11.0) like Gecko')
        )

    def test_apple(self):
        self.assertEqual(
            'Safari on iPad',
            agent_format('Mozilla/5.0 (iPad; U; CPU OS 4_2_1 like Mac OS X; ja-jp) '
                   'AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 '
                   'Mobile/8C148 Safari/6533.18.5')
        )
        self.assertEqual(
            'Safari on iPhone',
            agent_format('Mozilla/5.0 (iPhone; CPU iPhone OS 7_0 like Mac OS X) '
                   'AppleWebKit/537.51.1 (KHTML, like Gecko) Version/7.0 '
                   'Mobile/11A465 Safari/9537.53')
        )
        self.assertEqual(
            'Safari on OS X',
            agent_format('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) '
                   'AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 '
                   'Safari/536.26.17')
        )

    def test_android(self):
        # androids identify themselves as Safari to get the good stuff
        self.assertEqual(
            'Safari on Android',
            agent_format('Mozilla/5.0 (Linux; U; Android 1.5; de-de; HTC Magic '
                   'Build/CRB17) AppleWebKit/528.5+ (KHTML, like Gecko) '
                   'Version/3.1.2 Mobile Safari/525.20.1')
        )

    def test_firefox(self):
        self.assertEqual(
            'Firefox on Windows 7',
            agent_format('Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:22.0) '
                   'Gecko/20130328 Firefox/22.0')
        )

    def test_chrome(self):
        self.assertEqual(
            'Chrome on Windows 8.1',
            agent_format('Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 ('
                   'KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36')
        )

    def test_firefox_only(self):
        self.assertEqual("Firefox", agent_format("Not a legit OS Firefox/51.0"))

    def test_chrome_only(self):
        self.assertEqual("Chrome", agent_format("Not a legit OS Chrome/54.0.32"))

    def test_safari_only(self):
        self.assertEqual("Safari", agent_format("Not a legit OS Safari/5.2"))

    def test_linux_only(self):
        self.assertEqual("Linux", agent_format("Linux not a real browser/10.3"))

    def test_ipad_only(self):
        self.assertEqual("iPad", agent_format("iPad not a real browser/10.3"))

    def test_iphone_only(self):
        self.assertEqual("iPhone", agent_format("iPhone not a real browser/10.3"))

    def test_windowsxp_only(self):
        self.assertEqual("Windows XP", agent_format("NT 5.1 not a real browser/10.3"))

    def test_windowsvista_only(self):
        self.assertEqual("Windows Vista", agent_format("NT 6.0 not a real browser/10.3"))

    def test_windows7_only(self):
        self.assertEqual("Windows 7", agent_format("NT 6.1 not a real browser/10.3"))

    def test_windows8_only(self):
        self.assertEqual("Windows 8", agent_format("NT 6.2 not a real browser/10.3"))

    def test_windows81_only(self):
        self.assertEqual("Windows 8.1", agent_format("NT 6.3 not a real browser/10.3"))

    def test_windows_only(self):
        self.assertEqual("Windows", agent_format("Windows not a real browser/10.3"))
