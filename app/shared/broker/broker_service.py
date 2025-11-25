import logging
from faststream.rabbit import RabbitBroker
from app.shared.logs.logg import logger


broker = RabbitBroker(
    host="localhost",  # вместо postingbrokerservice
    port=5672,
    #virtualhost="prod"
    timeout=10.0,
    fail_fast=False,
    reconnect_interval=5.0,

    graceful_timeout=30.0,
    specification_url="/asyncapi",
    protocol="amqp",
    protocol_version="0.9.1",
    description="Posting RabbitMQ broker",

    logger=logger,
    log_level=logging.INFO,

    app_id="fast_api_broker",
    apply_types=True,
)
