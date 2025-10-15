const logger = require("../config/logConfig");
const appConfig = require("../config/appConfig.js");
const tokenService = require("./tokenService.js");
const fs = require('fs');
const {Kafka} = require('kafkajs');
const writeFile = require("./fileService");
const eventQueueService = require("./eventQueueService");
const kafkaSubscriptionSingleton = require('./kafkaSubscriptionSingleton');
const {Consumer} = require("kafka-node");
const {gracefulShutdown} = require("./commonServices");

function createConsumer() {
    const kafka = new Kafka({
        clientId: 'coletor',
        brokers: [`${appConfig.KAFKA_BROKER}:${appConfig.KAFKA_PORT}`], // Substitua pelos seus brokers
        ssl: {
            rejectUnauthorized: false,  // Ative isso apenas se você tiver certeza de que não quer validar o certificado do servidor, geralmente não é recomendado em produção
            ca: [fs.readFileSync(appConfig.CA, 'utf-8')],  // Substitua pelo caminho do seu truststore em formato PEM
            key: fs.readFileSync(appConfig.KEY, 'utf-8'),  // A chave privada extraída do keystore em formato PEM
            cert: fs.readFileSync(appConfig.PEM_CERT, 'utf-8'),  // O certificado extraído do keystore em formato PEM
            passphrase: appConfig.PASSPHRASE,  // A senha do keystore, se aplicável
        },
    });

    const consumer = kafka.consumer({
        groupId: appConfig.KAFKA_GROUP_ID,
    });
    logger.info("startListening: kafka consumer configured");
    return consumer;
}

function consume(message) {
    eventQueueService.pushEvent(message);
}

async function startListening() {

    logger.info("startListening to Kafka events");
    let consumer;

    // cria a subscription no kafka
    try {
        // cria o token
        await tokenService.createTopicSubscription("NSP-FAULT");
        logger.info("startListening: token created");
        // cria o consumer
        consumer = createConsumer();
        logger.info("startListening: consumer created");
    } catch (e) {
        logger.error("An error occurred while creating a subscription", e);
        await gracefulShutdown()
    }

    const run = async () => {
        // conecta ao kafka como um consumer
        await consumer.connect();
        logger.info("startListening: consumer connected");

        // se inscreve no tópico
        await consumer.subscribe({topic: kafkaSubscriptionSingleton.getTopicId(), fromBeginning: true});
        logger.info("startListening: consumer subscribed to a topic");

        await consumer.run({
            eachMessage: async ({topic, partition, message}) => {
                if (message) {
                    const messageString = message.value.toString()
                    const messageJson = JSON.parse(messageString);
                    logger.debug(`Received message JSON: ${JSON.stringify(messageJson, null, 2)}`);
                    consume(messageJson);
                }
            },
        });
    }

    run().catch(e => logger.error(`consumer error: ${e.message}`, e));


}

module.exports = {
    startListening,
}

