from typing import Protocol


class InsightsGatewayPort(Protocol):
	def generate_analysis_component(self, prompt, context=None):
		...


class InsightsService:
	def __init__(self, gateway: InsightsGatewayPort):
		self._gateway = gateway

	def generate_analysis_component(self, prompt, context=None):
		return self._gateway.generate_analysis_component(prompt, context)


def build_default_insights_service():
	from app.infrastructure.insights_gateway import LocalInsightsGatewayAdapter

	return InsightsService(gateway=LocalInsightsGatewayAdapter())


_default_insights_service = build_default_insights_service()


def generate_analysis_component(prompt, context=None):
	return _default_insights_service.generate_analysis_component(prompt, context)
