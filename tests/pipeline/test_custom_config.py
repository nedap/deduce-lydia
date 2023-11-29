import os
from pathlib import Path
from typing import Dict

from deduce import Deduce


def _get_individual_processors(deduce: Deduce) -> Dict:
    processors_by_group = deduce.processors._processors
    individual_processor_dict = {}
    for group_name, processors in processors_by_group.items():
        # Skip post-processing group, since they are added by default
        if group_name == "post_processing":
            continue
        individual_processor_dict.update(processors)
    return individual_processor_dict


test_configs_dir = Path(os.path.dirname(__file__)) / "configs_for_testing"


class TestDeduceWithCustomConfig:
    def test_phone_only(self):
        phone_config_path = Path(test_configs_dir, "phone_only.json")
        # Use config defaults = False otherwise it only replaces the content of phone annotator default config with the new config
        # but keeps all other annotators. This requires to copy the top level defaults from the default config into the new config
        deduce = Deduce(config_file=phone_config_path, use_config_defaults=False)

        processors = _get_individual_processors(deduce)

        assert len(processors) == 1

        text = "Mijn telefoonnummer is 06-12345678. En mijn naam is Elsa van der Wal."
        result = deduce.deidentify(text)

        assert len(result.annotations) == 1
        assert (
            result.deidentified_text
            == "Mijn telefoonnummer is <TELEFOONNUMMER-1>. En mijn naam is Elsa van der Wal."
        )

    def test_email_phone_url(self):
        phone_config_path = Path(test_configs_dir, "phone_email_url.json")
        deduce = Deduce(config_file=phone_config_path, use_config_defaults=False)

        processors = _get_individual_processors(deduce)

        assert len(processors) == 3

        text = "Mijn telefoonnummer is 06-12345678. En mijn naam is Elsa van der Wal. elsa_wal@hotmail.com, homepage: https://www.elsa.co.uk"
        result = deduce.deidentify(text)

        assert len(result.annotations) == 3
        assert (
            result.deidentified_text
            == "Mijn telefoonnummer is <TELEFOONNUMMER-1>. En mijn naam is Elsa van der Wal. <EMAIL-1>, homepage: <URL-1>"
        )

    def test_first_names_lookup(self):
        phone_config_path = Path(test_configs_dir, "first_names_lookup.json")
        deduce = Deduce(config_file=phone_config_path, use_config_defaults=False)

        processors = _get_individual_processors(deduce)

        # are 2 because when a name processor is added the person annotation converter is added automatically
        assert len(processors) == 2

        text = "Mijn telefoonnummer is 06-12345678. En mijn naam is Elsa van der Wal. elsa_wal@hotmail.com, homepage: https://www.elsa.co.uk"
        result = deduce.deidentify(text)

        assert len(result.annotations) == 1
        assert (
            result.deidentified_text
            == "Mijn telefoonnummer is 06-12345678. En mijn naam is <PERSOON-1> van der Wal. elsa_wal@hotmail.com, homepage: https://www.elsa.co.uk"
        )
