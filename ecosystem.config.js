module.exports = {
  apps: [
    {
      name: "cv-job-hunter",
      script: "agent.py",
      interpreter: "python3",
      cron_restart: "0 6 * * *", // 06:00 UTC = 08:00 Berlin (CEST/summer); will be 07:00 Berlin in winter (CET) — adjust to "0 7 * * *" then
      autorestart: false,
      watch: false,
    },
  ],
};
