const appConfig = require("../config/appConfig");
const apiCredentials = require("../config/nokiaApiCredentials");
const logger = require("../config/logConfig");
const axios = require("axios");
const https = require("https");
const tokenSingleton = require('./tokenSingleton');
const kafkaSubscriptionSingleton = require('./kafkaSubscriptionSingleton');
const cron = require('node-cron');
const redisService = require("./redisService");


const httpInstance = axios.create({
    httpsAgent: new https.Agent({
        rejectUnauthorized: false
    })
});


async function setToken() {
    let status_code = null;
    try {
        const GET_TOKEN_BODY = {
            grant_type: "client_credentials",
        };

        const response = await httpInstance.post(`https://${appConfig.API_HOST}:${appConfig.API_PORT}/rest-gateway/rest/api/v1/auth/token`, GET_TOKEN_BODY, {
            headers: {
                "Content-Type": "application/json",
                Authorization: `Basic ${apiCredentials.TOKEN}`,
            }
        });

        status_code = response.status;
        logger.info(`get token response status code : ${status_code}`);
        await redisService.updateToken(response.data.access_token, response.data.refresh_token);
        logger.info(`Authorization Token: ${apiCredentials.TOKEN}`);
        logger.info(`Access Token: ${tokenSingleton.getAccessToken()}`);
        logger.info(`Refresh Token: ${tokenSingleton.getRefreshToken()}`);

    } catch (e) {
        logger.error("An error occurred while requesting API for Token", status_code);
    }
}


async function createTopicSubscription(category) {

    const GET_SUBSCRIPTION_BODY = {
        categories: [
            {
                name: category,
                propertyFilter: "severity = 'warning'"
            }
        ]
    };

    let statusCode = null;
    const url = `https://${appConfig.SUBSCRIPTION_HOST}:${appConfig.SUBSCRIPTION_PORT}/nbi-notification/api/v1/notifications/subscriptions`;
    logger.info(`Subscribing to topic via url: ${url}`);
    try {
        const response = await httpInstance.post(url, GET_SUBSCRIPTION_BODY, {
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${tokenSingleton.getAccessToken()}`,
            }
        });

        statusCode = response.status;
        const subscriptionInfo = {
            subscriptionId: response.data.response.data.subscriptionId,
            topicId: response.data.response.data.topicId,
            expiresAt: response.data.response.data.expiresAt
        }
        logger.info(`Subscription Info: ${JSON.stringify(subscriptionInfo)}`);
        await redisService.updateSubscriptionInfo(subscriptionInfo);
    } catch (error) {
        logger.error("An error occurred while subscribing to kafka topic", statusCode);
    }
}

async function revokeToken() {

    const accessToken = tokenSingleton.getAccessToken();
    if (!accessToken) {
        logger.warn("No token to revoke");
        return;
    }

    const token_revoke_string = `token=${accessToken}&token_type_hint=token`;
    logger.info(`Revoking token string token=${accessToken}&token_type_hint=token`);
    await httpInstance.post(`https://${appConfig.API_HOST}:${appConfig.API_PORT}/rest-gateway/rest/api/v1/auth/revocation`, token_revoke_string, {
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': `Basic ${apiCredentials.TOKEN}`,
        }
    }).then((response) => {
        logger.info(`Token: ${accessToken} revoked successfully`);
    }).catch((error) => {
        logger.error("An error occurred while requesting API for token revocation", error);
    });
}

async function refreshToken() {
    const REFRESH_BODY = {
        grant_type: "refresh_token",
        refresh_token: tokenSingleton.getRefreshToken()
    }

    httpInstance.post(`https://${appConfig.API_HOST}:${appConfig.API_PORT}/rest-gateway/rest/api/v1/auth/token`, REFRESH_BODY, {
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            Authorization: `Basic ${apiCredentials.TOKEN}`,
        }
    }).then((response) => {
        logger.info(`Refreshing token ${tokenSingleton.getRefreshToken()}`);
        redisService.updateToken(response.data.access_token, response.data.refresh_token);
    }).catch((error) => {
        logger.error("An error occurred while refreshing Token", error);
    });
}


setInterval(async () => await renewAllTokensAndSubscriptions(), 30 * 60 * 1000); // 50 minutos


async function renewAllTokensAndSubscriptions() {
    await refreshToken();
    await renewSubscription();
}

async function renewSubscription() {

    logger.info(`Renewing subscription ${kafkaSubscriptionSingleton.getSubscriptionId()}`);
    httpInstance.post(`https:///${appConfig.SUBSCRIPTION_HOST}:${appConfig.SUBSCRIPTION_PORT}/nbi-notification/api/v1/notifications/subscriptions/${kafkaSubscriptionSingleton.getSubscriptionId()}/renewals`, {}, {
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${tokenSingleton.getAccessToken()}`,
        }
    }).then((response) => {
        logger.info(`Subscription ${kafkaSubscriptionSingleton.getSubscriptionId()} renewed successfully`);
    }).catch((error) => {
        logger.error("An error occurred while renewing subscription", error);
    });
}

module.exports = {
    httpInstance,
    renewSubscription,
    setToken,
    revokeToken,
    refreshToken,
    createTopicSubscription
}