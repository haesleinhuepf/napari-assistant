call python -m pip install --user --upgrade setuptools wheel

call python setup.py sdist bdist_wheel

call python -m pip install --user --upgrade twine

set TWINE_USERNAME=__token__
set TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcCJDEyYzM5MDBjLTg4ZmYtNDhmZC05ZTRiLTczMzc2MThlNjNlZAACKlszLCJmMzMyMmMwZi1iZTI0LTRiYWUtOTUxZS1hNGU5YmU2M2RlMWMiXQAABiDoX0JmgKtiQD_eJ5B6vSKJWeNDsP9i6JuzgYkwkF14dg

call python -m twine upload dist/*
