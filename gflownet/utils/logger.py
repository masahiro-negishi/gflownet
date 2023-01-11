import wandb
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np


class Logger:
    """
    Utils functions to compute and handle the statistics (saving them or send to
    wandb). It can be passed on to querier, gfn, proxy, ... to get the
    statistics of training of the generated data at real time
    """

    def __init__(self, config, project_name, sampler, run_name=None, tags=None):
        self.config = config
        if run_name is None:
            date_time = datetime.today().strftime("%d/%m-%H:%M:%S")
            run_name = "{}".format(
                date_time,
            )
        self.run = wandb.init(config=config, project=project_name, name=run_name)
        self.add_tags(config.log.tags)
        self.sampler = sampler
        self.context = "0"

    def add_tags(self, tags):
        self.run.tags = self.run.tags + tags

    def set_context(self, context):
        self.context = str(context)

    def log_metric(self, key, value, use_context=True):
        if use_context:
            key = self.context + "/" + key
        wandb.log({key: value})

    def log_histogram(self, key, value, use_context=True):
        # need this condition for when we are training gfn without active learning and context = ""
        # we can't make use_context=False because then when the same gfn is used with AL, context won't be recorded (undesirable)
        if use_context:
            key = self.context + "/" + key
        fig = plt.figure()
        plt.hist(value)
        plt.title(key)
        plt.ylabel("Frequency")
        plt.xlabel(key)
        fig = wandb.Image(fig)
        wandb.log({key: fig})

    def log_metrics(self, metrics, step, use_context=True):
        if use_context:
            for key, _ in metrics.items():
                key = self.context + "/" + key
        wandb.log(metrics, step)

    def log_sampler_train(self, rewards, proxy_vals, states_term, data, it):
        if it % self.sampler.train == 0:
            self.logger.log_metrics(
                dict(
                    (
                        [
                            "mean_reward{}".format(self.al_iter),
                            "max_reward{}".format(self.al_iter),
                            "mean_proxy{}".format(self.al_iter),
                            "min_proxy{}".format(self.al_iter),
                            "max_proxy{}".format(self.al_iter),
                            "mean_seq_length{}".format(self.al_iter),
                            "batch_size{}".format(self.al_iter),
                        ],
                        [
                            np.mean(rewards),
                            np.max(rewards),
                            np.mean(proxy_vals),
                            np.min(proxy_vals),
                            np.max(proxy_vals),
                            np.mean([len(state) for state in states_term]),
                            len(data),
                        ],
                    )
                ),
                self.use_context,
                step=it,
            )

    def log_sampler_test(self, corr, data_logq, it):
        if it % self.sampler.test == 0:
            self.logger.log_metrics(
                dict(
                    zip(
                        [
                            "test_corr_logq_score",
                            "test_mean_log",
                        ],
                        [
                            corr[0, 1],
                            np.mean(data_logq),
                        ],
                    )
                ),
                self.use_context,
                step=it,
            )

    def log_sampler_oracle(self, energies, it):
        if it % self.sampler.oracle == 0:
            dict_topk = {}
            for k in self.oracle_k:
                mean_topk = np.mean(energies[:k])
                dict_topk.update(
                    {"oracle_mean_top{}{}".format(k, self.al_iter): mean_topk}
                )
            self.logger.log_metrics(dict_topk, self.use_context)

    def end(self):
        wandb.finish()
