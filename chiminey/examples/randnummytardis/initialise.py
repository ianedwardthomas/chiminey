# Copyright (C) 2014, RMIT University

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import logging
from chiminey.initialisation import CoreInitial
from chiminey.smartconnectorscheduler import models


logger = logging.getLogger(__name__)

class RandNumMyTardisInitial(CoreInitial):
    def define_configure_stage(self):
        configure_package = "chiminey.examples.randnummytardis.randconfigure.RandConfigure"
        configure_stage, _ = models.Stage.objects.get_or_create(
            name="rand2configure",
            description="This is the RandNum configure stage",
            parent=self.define_parent_stage(),
            package=configure_package,
            order=0)
        configure_stage.update_settings({
            u'http://rmit.edu.au/schemas/system':
                {
                    u'random_numbers': 'file://127.0.0.1/randomnums.txt'
                },
        })
        return configure_stage

    def define_bootstrap_stage(self):
        bootstrap_stage = super(RandNumMyTardisInitial, self).define_bootstrap_stage()
        bootstrap_stage.update_settings(
            {
                u'http://rmit.edu.au/schemas/stages/setup':
                    {
                        u'payload_source': 'local/payload_randnum',
                        u'payload_destination': 'randnum_dest',
                        u'payload_name': 'process_payload',
                        u'filename_for_PIDs': 'PIDs_collections',
                    },
            })
        return bootstrap_stage

    def define_transform_stage(self):
        transform_package = "chiminey.examples.randnummytardis.randtransform.RandTransform"
        transform_stage, _ = models.Stage.objects.get_or_create(name="rand2transform",
            description="This is the RandNum transform stage",
            parent=self.define_parent_stage(),
            package=transform_package,
            order=50)
        transform_stage.update_settings({})
        return transform_stage


    def get_ui_schema_namespace(self):
        RMIT_SCHEMA = "http://rmit.edu.au/schemas"
        schemas = [
                RMIT_SCHEMA + "/input/system/compplatform",
                RMIT_SCHEMA + "/input/system/cloud",
                RMIT_SCHEMA + "/input/location/output",
                RMIT_SCHEMA + "/input/mytardis"
                ]
        return schemas