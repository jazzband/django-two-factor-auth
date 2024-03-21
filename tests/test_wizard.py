from django.template.loader import render_to_string
from django.test import SimpleTestCase

class TestWizardActionsTemplate(SimpleTestCase):
    def test_render_template_authenticated(self):
        template_name = 'two_factor/_wizard_actions.html' 

        # Render the template
        rendered_template = self.render_template(template_name, {'user': {'is_authenticated': True}, 'cancel_url': '/cancel', 'wizard': {'steps': {'prev': 'previous_step'}}})

        # Assert that the "Sign in" button is not present for authenticated users
        self.assertNotIn('<button type="submit" name="login" class="btn btn-dark">Sign in</button>', rendered_template)

    def test_render_template_not_authenticated(self):
        template_name = 'two_factor/_wizard_actions.html'

        # Render the template
        rendered_template = self.render_template(template_name, {'user': {'is_authenticated': False}})

        # Assert that the "Sign in" button is present for non-authenticated users
        self.assertIn('Sign in', rendered_template)

    def render_template(self, template_name, context):
        # Render the template with the context
        return render_to_string(template_name, context)
