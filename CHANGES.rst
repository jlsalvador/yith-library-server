0.3 (2015-07-07)
----------------
- New features:

  - Updated all the dependencies to newer versions
  - Replaced persistence layer from MongoDB to PostgreSQL (Lorenzo Gil)
  - New UI based on Bootstrap 3 (Lorenzo Gil)
  - Assets concatenation and minification using webassets (Lorenzo Gil)
  - Replaced custom oauth2 support with the oauthlib
    implementation (Lorenzo Gil)
  - Reused package dependencies information between requirements.txt
    and setup.py (Fidel Ramos)
  - Added back Python 3 support (Lorenzo Gil)
  - Removed the custom DatetimeService and use freezegun instead for
    mocking datetimes in tests (Lorenzo Gil)
  - Add Microsoft Live Connect as a new IdP (Lorenzo Gil)
  - Add a Contributions page with donations support via PayPal (Lorenzo Gil)

- Buf fixes:

  - Lots of fixed contributed by Lorenzo Gil, Sergio Rus and Alejandro Blanco

0.2 (2013-02-03)
----------------
- New features:

  - Import/export of password collections
  - Periodic mailing of password backup files
  - New report to get statistics of usage
  - Rename old usage report to users since it just list the users
  - Improve gravatar icon style in the header
  - Make Persona logout more robust
  - Improve the marketing (Twitter and Github links)

- Regressions:

  - Remove Python 3 support because of a pyramid_mailer's bug. The bug (#24)
    has been fixed but no new release has been made as of this writing.

0.1 (2013-01-13)
----------------
- Oauth2 protocol to access the passwords with a RESTful API
- Facebook, Google, Mozilla Persona and Twitter authentication methods
- Account merging to allow several authentication methods for one account
- User profile with Gravatar integration
- Account removal
- Localized to English and Spanish languages
- Google Analytics support that users can avoid
- 100% test coverage
- Landing, terms of service and contact pages
