class EvidenceVerifier:

    OFFICIAL_DOMAINS = [
        "sec.gov",
        "sedar.com",
        "nasdaq.com",
        "nyse.com"
    ]

    def verify(self, claim, source):

        for domain in self.OFFICIAL_DOMAINS:

            if domain.lower() in source.url.lower():

                claim.verified = True
                claim.confidence = 0.95

                return claim

        claim.verified = False
        claim.confidence = 0.45

        return claim
