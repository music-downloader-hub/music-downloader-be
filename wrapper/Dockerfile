FROM ubuntu:latest

WORKDIR /app

# Copy tar và giải nén ra binary 'wrapper'
COPY wrapper.x86_64.tar.gz /tmp/wrapper.tar.gz
RUN tar -xzf /tmp/wrapper.tar.gz -C /app && rm /tmp/wrapper.tar.gz

# Copy the rootfs directory
COPY rootfs /app/rootfs

# Make it executable
RUN chmod +x /app/wrapper
ENV args=""
CMD ["bash", "-c", "./wrapper ${args}"]

EXPOSE 10020 20020