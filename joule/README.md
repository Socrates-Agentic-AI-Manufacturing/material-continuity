# Material Continuity Joule capability

This first capability is read-only. It reports the current synthetic exposure
case and cannot approve, release, or write to SAP.

Create an HTTP destination named `MATERIAL_CONTINUITY_API` in the same BTP
subaccount as Joule:

```text
URL: https://material-continuity-antek2-rl.cfapps.ap10.hana.ondemand.com
Proxy Type: Internet
Authentication: BasicAuthentication
User: same value as MATERIAL_CONTINUITY_JOULE_USER
Password: same value as MATERIAL_CONTINUITY_JOULE_PASSWORD
```

Set the matching values on Cloud Foundry without committing them:

```powershell
cf set-env material-continuity-antek2-rl MATERIAL_CONTINUITY_JOULE_USER <user>
cf set-env material-continuity-antek2-rl MATERIAL_CONTINUITY_JOULE_PASSWORD <password>
cf restage material-continuity-antek2-rl
```

Deploy from the `joule` directory:

```powershell
joule deploy --compile .\material_continuity
joule list
joule launch material_continuity_capability
```
