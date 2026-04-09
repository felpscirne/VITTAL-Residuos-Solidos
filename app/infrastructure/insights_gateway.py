from app.services.ai_service import generate_analysis_component as _generate_analysis_component


class LocalInsightsGatewayAdapter:
    def generate_analysis_component(self, prompt, context=None):
        return _generate_analysis_component(prompt)


_default_gateway_adapter = LocalInsightsGatewayAdapter()


def generate_analysis_component(prompt, context=None):
    return _default_gateway_adapter.generate_analysis_component(prompt, context)
