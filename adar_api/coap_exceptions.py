from aiocoap import Message


class CoapException(Exception):
    pass


class CoapErrorException(CoapException):
    def __init__(self, *args, **kwargs):
        """Initialize CoapErrorException with optional CoAP response.

        Args:
            *args: Variable length argument list passed to parent exception
            **kwargs: Arbitrary keyword arguments, may include 'response' key for CoAP Message
        """
        super().__init__(*args)
        self.response: Message = kwargs.get("response")
