const fs = require("fs");


const APP_HOST = 'localhost'
const APP_PORT = 3000;

const API_HOST = '10.73.0.181';
const API_PORT = 8443;

const AUTHORIZATION_HOST = '10.73.0.181';
const AUTHORIZATION_PORT = 80;

const SUBSCRIPTION_HOST = '10.73.0.181';
const SUBSCRIPTION_PORT = 8544;

const KAFKA_BROKER = '10.73.0.181';
const KAFKA_PORT = 9193;

const CONTENT_FILE = 'content/input.json';
const SUBSCRIPTION_TIMEOUT = 3400 * 1000;
const API_QUERY_REQUEST_INTERVAL = 10 * 1000; //10 sec
const CURRENT_ROUTE_RETENTION_TIME = 7;

const KAFKA_GROUP_ID = 'dev-consumer-group'
//const KAFKA_GROUP_ID = 'kpi-consumer-group'

const CA = 'config/certs/nsp.truststore';
const KEY = 'config/certs/key.pem';
const PEM_CERT = 'config/certs/nfmt.pem';
const PASSPHRASE = 'NokiaNfmt1!';

module.exports = {
    REDIS_HOST,
    REDIS_PORT,
    APP_HOST,
    APP_PORT,
    KAFKA_BROKER,
    KAFKA_PORT,
    API_HOST,
    API_PORT,
    AUTHORIZATION_HOST,
    AUTHORIZATION_PORT,
    CONTENT_FILE,
    SUBSCRIPTION_HOST,
    SUBSCRIPTION_PORT,
    SUBSCRIPTION_TIMEOUT,
    API_QUERY_REQUEST_INTERVAL,
    CA,
    KEY,
    PEM_CERT,
    PASSPHRASE,
    CURRENT_ROUTE_RETENTION_TIME,
    KAFKA_GROUP_ID
}







