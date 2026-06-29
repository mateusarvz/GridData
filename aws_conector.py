import os
import psycopg2
from psycopg2.extras import RealDictCursor


DEFAULT_HOST = 'database-1.cluster-cdwskm6cwbni.us-east-2.rds.amazonaws.com'
DEFAULT_PORT = 5432
DEFAULT_DB = 'postgres'
DEFAULT_USER = 'postgres'
DEFAULT_REGION = 'us-east-2'


def _resolve_password(password=None, auth_token=None):
	"""Resolve the password/auth token from explicit values or environment variables."""
	if auth_token:
		return auth_token
	if password:
		return password
	for key in ('AWS_RDS_IAM_TOKEN', 'RDS_IAM_TOKEN', 'DB_PASSWORD', 'RDS_PASSWORD'):
		value = os.getenv(key)
		if value:
			return value
	raise RuntimeError("No RDS password or IAM token found. Set AWS_RDS_IAM_TOKEN or DB_PASSWORD.")


def get_connection(host=None, port=None, dbname=None, user=None, region=None, connect_timeout=10, password=None, auth_token=None):
	"""Connect to RDS using either a direct password or an IAM auth token."""
	host = host or os.getenv('RDSHOST') or os.getenv('DB_HOST') or DEFAULT_HOST
	port = int(port or os.getenv('RDS_PORT') or DEFAULT_PORT)
	user = user or os.getenv('DB_USER') or os.getenv('RDS_USER') or DEFAULT_USER
	dbname = dbname or os.getenv('DB_NAME') or DEFAULT_DB
	region = region or os.getenv('AWS_REGION') or os.getenv('AWS_DEFAULT_REGION') or DEFAULT_REGION
	password_value = _resolve_password(password=password, auth_token=auth_token)

	conn_kwargs = dict(
		host=host,
		port=port,
		user=user,
		dbname=dbname,
		sslmode='require',
		connect_timeout=connect_timeout,
		cursor_factory=RealDictCursor,
		password=password_value,
	)

	return psycopg2.connect(**conn_kwargs)


if __name__ == '__main__':
	print('Arquivo de conexão. Importe get_connection() em outros módulos.')