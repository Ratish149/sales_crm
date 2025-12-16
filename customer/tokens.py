from django.contrib.auth.tokens import PasswordResetTokenGenerator


class CustomerTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Ensure that the token is invalid if the password is changed
        return str(user.pk) + str(timestamp) + str(user.password)


customer_token_generator = CustomerTokenGenerator()
