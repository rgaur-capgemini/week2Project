# Operational Runbooks

This directory contains step-by-step operational procedures for the RAG Chatbot production system.

## 📚 Available Runbooks

### Emergency Procedures
- **[rollback.md](rollback.md)** - Emergency deployment rollback procedures
- **[emergency-scaling.md](emergency-scaling.md)** - Manual scaling during incidents

### Maintenance Operations
- **[backup-restore.md](backup-restore.md)** - Backup and disaster recovery procedures
- **[certificate-rotation.md](certificate-rotation.md)** - TLS certificate and credential rotation
- **[database-maintenance.md](database-maintenance.md)** - Firestore and Redis maintenance

### Routine Operations
- **[scaling-operations.md](scaling-operations.md)** - Planned scaling procedures
- **[log-management.md](log-management.md)** - Log archival and cleanup
- **[index-rebuild.md](index-rebuild.md)** - Vector index maintenance

### Compliance & Security
- **[security-audit.md](security-audit.md)** - Security audit procedures
- **[access-review.md](access-review.md)** - IAM access reviews

## 🎯 How to Use These Runbooks

1. **Emergency Situations**: Start with the most specific runbook (e.g., rollback.md)
2. **Routine Maintenance**: Follow the weekly schedule in each runbook
3. **First Time**: Read the entire runbook before executing
4. **Document**: Log all actions taken in the incident log or maintenance log

## 📋 Runbook Format

Each runbook follows this structure:
- **Purpose**: What this procedure accomplishes
- **Prerequisites**: Required access, tools, and preparations
- **Procedure**: Step-by-step instructions with commands
- **Verification**: How to confirm success
- **Rollback**: How to undo if something goes wrong
- **References**: Related documentation

## ⚠️ Important Notes

- **Always test in staging first** when possible
- **Take snapshots** before major changes
- **Notify the team** via Slack #incidents or #maintenance
- **Update documentation** if you discover outdated information
- **Create post-mortem** for any incidents

## 🔗 Related Documentation

- [SRE Runbook](../SRE_RUNBOOK.md) - Incident response procedures
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Initial deployment procedures
- [Architecture](../architecture.md) - System architecture overview

---

**Last Updated**: February 2026  
**Maintained By**: SRE Team
