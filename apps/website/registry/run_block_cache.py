from dataclasses import dataclass, field

from .models import (
    RunSubmissionEventBlock,
    VerifiedRunEventBlock,
)
from .run_exports import GENESIS_HASH, decode_run_export


@dataclass
class VerifiedBlockCache:
    prepared: dict = field(default_factory=dict)
    starting_hashes: dict = field(default_factory=dict)

    def prepare(self, descriptors):
        checksums = []
        previous_hash = GENESIS_HASH
        for descriptor in descriptors:
            checksum = descriptor.get("checksum")
            checksums.append(checksum)
            self.starting_hashes[checksum, descriptor.get("firstSequence")] = previous_hash
            previous_hash = descriptor.get("lastHash")
        rows = VerifiedRunEventBlock.objects.filter(checksum__in=checksums)
        self.prepared = {
            (
                row.checksum,
                row.first_sequence,
                row.last_sequence,
                row.event_count,
                row.starting_hash,
                row.last_hash,
            ): row
            for row in rows
        }

    def get(self, descriptor):
        checksum = descriptor["checksum"]
        first = descriptor["firstSequence"]
        starting_hash = self.starting_hashes[checksum, first]
        row = self.prepared.get(
            (
                checksum,
                first,
                descriptor["lastSequence"],
                descriptor["count"],
                starting_hash,
                descriptor["lastHash"],
            )
        )
        if not row:
            return None
        return {"canonical": bytes(row.canonical), "events": row.events}


def decode_run_export_cached(value):
    return decode_run_export(value, block_cache=VerifiedBlockCache())


def attach_verified_blocks(submission, decoded):
    links = []
    for item in decoded.event_blocks:
        descriptor = item["descriptor"]
        block, _ = VerifiedRunEventBlock.objects.get_or_create(
            checksum=descriptor["checksum"],
            first_sequence=descriptor["firstSequence"],
            starting_hash=item["starting_hash"],
            last_hash=descriptor["lastHash"],
            defaults={
                "last_sequence": descriptor["lastSequence"],
                "event_count": descriptor["count"],
                "canonical": item["canonical"],
                "events": item["events"],
            },
        )
        links.append(
            RunSubmissionEventBlock(
                submission=submission,
                block=block,
                position=item["position"],
            )
        )
    RunSubmissionEventBlock.objects.bulk_create(links)
