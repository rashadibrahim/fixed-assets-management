from flask_restx import Api, fields

# Create a Flask-RESTx API instance
api = Api(
    version='1.0',
    title='Fixed Assets Management API',
    description='A comprehensive API for managing fixed assets, warehouses, branches, users, and job roles with role-based permissions',
    doc='/api/docs',  # Swagger UI will be available at /api/docs
    ui=True,
    contact='API Support',
    contact_email='support@example.com',
    license='MIT',
    license_url='https://opensource.org/licenses/MIT',
    # Customize Swagger UI appearance
    swagger_ui_bundle_js='https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui-bundle.min.js',
    swagger_ui_css='https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/4.15.5/swagger-ui.min.css',
    # Add JWT authentication
    authorizations={
        'Bearer Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
        }
    },
    security='Bearer Auth'
)

# Define API namespaces for different resource groups
branches_ns = api.namespace('branches', description='Branch management operations')
warehouses_ns = api.namespace('warehouses', description='Warehouse management operations')
assets_ns = api.namespace('assets', description='Fixed asset management operations')
auth_ns = api.namespace('auth', description='Authentication and user management operations')
job_roles_ns = api.namespace('jobroles', description='Job role and permissions management operations')

# Define common response codes for documentation
response_codes = {
    200: 'Success',
    201: 'Created',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    422: 'Validation Error',
    500: 'Internal Server Error'
}

# Helper function to add standard responses to API endpoints
def add_standard_responses(api_doc):
    """Add standard response codes to an API endpoint documentation"""
    for code, desc in response_codes.items():
        api_doc.response(code, desc)
    return api_doc