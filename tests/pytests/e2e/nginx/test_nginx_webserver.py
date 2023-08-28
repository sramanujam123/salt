"""
tests.pytests.e2e.nginx.nginx_webserver
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test webserver version
"""

import logging
import pathlib
import time
import types
import requests

import pytest

import salt.utils.event
import salt.utils.reactor
from salt.serializers import yaml
from tests.support.helpers import PRE_PYTEST_SKIP_REASON

pytestmark = [
    pytest.mark.slow_test,
    pytest.mark.windows_whitelisted,
    pytest.mark.skip_on_windows(reason=PRE_PYTEST_SKIP_REASON),
]

log = logging.getLogger(__name__)


def test_nginx_webserver_version_check(
    salt_minion, salt_master, salt_cli
):
    """
    install nginx
    """
    file_contents_nginx_conf = """
        user nginx;
        worker_processes auto;
        error_log /var/log/nginx/error.log notice;
        pid /run/nginx.pid;
        # Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
        
        include /usr/share/nginx/modules/*.conf;
        events {
            worker_connections 1024;
        }
        
        http {
            log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                              '$status $body_bytes_sent "$http_referer" '
                              '"$http_user_agent" "$http_x_forwarded_for"';
            access_log  /var/log/nginx/access.log  main;
            sendfile            on;
            tcp_nopush          on;
            keepalive_timeout   65;
            types_hash_max_size 4096;
            include             /etc/nginx/mime.types;
            default_type        application/octet-stream;
            # Load modular configuration files from the /etc/nginx/conf.d directory.
            # See http://nginx.org/en/docs/ngx_core_module.html#include
            # for more information.
            include /etc/nginx/conf.d/*.conf;
        
            server {
                listen       80;
                listen       [::]:80;
                server_name  _;
                root         {{ root_path }}
                # Load configuration files for the default server block.                                                                                                                     
                include /etc/nginx/default.d/*.conf;
                error_page 404 /404.html;
                location = /404.html {
                }
                error_page 500 502 503 504 /50x.html;
                location = /50x.html {
                }
            }
        }
    """
    file_contents_index_html = """
        <!doctype html>
        <html>
          <head>
            <title>Version 1.0 of website</title>
          </head>
          <body>
            <p>Release 1.0 was successful</p>
          </body>
        </html>
    """
    sls_contents = """
        {% set root_path = "/usr/share/nginx/html/" %}
    
        install_nginx:
          pkg.installed:
            - name: nginx
        
        nginx_conf:
          file.managed:
            - name: /etc/nginx/nginx.conf
            - source: salt://files/nginx.conf
            - template: jinja
            - defaults:
                root_path: {{ root_path }};
        
        nginx_website:
          file.managed:
            - name: {{ root_path }}index.html
            - makedirs: True
            - source: salt://files/index.html
        
        start_nginx:
          service.running:
            - name: nginx
            - reload: True
            - restart: True
            - enable: True
            - watch:
              - file: nginx_conf
              - file: nginx_website
    """

    with pytest.helpers.temp_file("files/nginx.conf", file_contents_nginx_conf, salt_master.state_tree.base.write_path),pytest.helpers.temp_file("files/index.html", file_contents_index_html, salt_master.state_tree.base.write_path), pytest.helpers.temp_file("nginx.sls", sls_contents, salt_master.state_tree.base.write_path):
        ret = salt_cli.run("state.sls", "nginx", minion_tgt=salt_minion.id)

        assert ret.returncode == 0
        # run webserver
        req = requests.get("http://localhost")
        contents = req.text
        print(contents)
        assert (
            "Release 1.0 was successful"
            in contents
        )

        sls_contents_new = sls_contents.replace("/usr/share/nginx/html", "/usr/share/nginx-new/html")
        file_contents_index_html_new = file_contents_index_html.replace("1.0", "2.0")
        with pytest.helpers.temp_file("files/nginx.conf", file_contents_nginx_conf, salt_master.state_tree.base.write_path),pytest.helpers.temp_file("files/index.html", file_contents_index_html_new, salt_master.state_tree.base.write_path), pytest.helpers.temp_file("nginx.sls", sls_contents_new, salt_master.state_tree.base.write_path):
            ret = salt_cli.run("state.sls", "nginx", minion_tgt=salt_minion.id)

            assert ret.returncode == 0
            # run webserver
            req = requests.get("http://localhost")
            contents = req.text
            print(contents)
            assert (
                "Release 2.0 was successful"
                in contents
            )
