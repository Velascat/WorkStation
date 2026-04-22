# WorkStation 9router Removal

- Base compose no longer starts or waits on 9router.
- `.env.example`, startup flow, and provider docs no longer instruct operators to configure `config/9router`.
- Health scripts validate the current stack instead of a retired proxy topology.
- Dev overrides, status scripts, and endpoint/service examples no longer carry `ninerouter`.
