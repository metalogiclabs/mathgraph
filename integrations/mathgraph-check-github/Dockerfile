# Build with: docker build -f integrations/mathgraph-check-github/Dockerfile integrations/mathgraph-check-github
# Secrets must be injected by the runtime; this image contains none.
FROM node:22-alpine
WORKDIR /srv/mathgraph-check
COPY core.mjs webhook.mjs ./
ENV NODE_ENV=production
ENV PORT=8787
USER node
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=4s --retries=3 CMD node -e 'fetch("http://127.0.0.1:"+process.env.PORT+"/health").then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))'
CMD ["node","webhook.mjs"]
