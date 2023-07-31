FROM nginxinc/nginx-unprivileged:latest
COPY public /usr/share/nginx/html
COPY default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
