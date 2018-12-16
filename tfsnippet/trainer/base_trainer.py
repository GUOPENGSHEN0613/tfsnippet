from tfsnippet.scaffold import TrainLoop
from tfsnippet.utils import (ensure_variables_initialized,
                             get_default_session_or_error,
                             DocInherit)

from .dynamic_values import AnnealingDynamicValue
from .hooks import HookPriority, HookList
from .evaluator import Evaluator

__all__ = ['BaseTrainer']


def check_epochs_and_steps_arg(epochs=None, steps=None):
    if (epochs is not None and steps is not None) or \
            (epochs is None and steps is None):
        raise ValueError('One and only one of `epochs` and `steps` should '
                         'be specified.')


@DocInherit
class BaseTrainer(object):
    """
    Base class for all trainers.

    All the trainers provided in :mod:`tfsnippet.trainer` are not
    designed to take control of the training totally, which is often
    assumed in other libraries such as Keras.  Instead, it just takes
    responsibility of assembling different steps of a training process
    together, and run the main training loop.  So it is usually the caller's
    responsibility to derive his training operation from a certain TensorFlow
    optimizer, and pass it to a proper trainer.

    See Also:
        :class:`tfsnippet.trainer.LossTrainer`
    """

    def __init__(self, loop):
        """
        Initialize the internal states of :class:`BaseTrainer`.

        Args:
            loop (TrainLoop): The training loop object.
        """
        self._loop = loop

        self._before_epochs = HookList()
        self._after_epochs = HookList()
        self._before_steps = HookList()
        self._after_steps = HookList()
        self._hook_lists = (
            self._before_epochs, self._before_steps, self._after_steps,
            self._after_epochs
        )

        self._is_fitting = False

    @property
    def loop(self):
        """
        Get the training loop object.

        Returns:
            TrainLoop: The training loop object.
        """
        return self._loop

    def run(self):
        """Run training loop."""
        if self._is_fitting:
            raise RuntimeError('`run()` is not re-entrant.')
        self._is_fitting = True
        try:
            # initialize global training status
            session = get_default_session_or_error()
            ensure_variables_initialized()
            self.loop.print_training_summary()

            # initialize internal status
            for hook_list in self.hook_lists:
                hook_list.reset()

            for epoch in self.loop.iter_epochs():
                # run before epoch hook
                self.before_epochs.call_hooks()

                # run steps of this epoch
                for payload in self._iter_steps():
                    # run before step hook
                    self.before_steps.call_hooks()

                    # run the step
                    self._run_step(session, payload)

                    # run after step hook
                    self.after_steps.call_hooks()

                # run after epoch hook
                self.after_epochs.call_hooks()
        finally:
            self._is_fitting = False

    def _iter_steps(self):
        """
        Subclasses should override this to iterate through steps.

        A common implementation of :meth:`_iter_steps()` might be::

            def _iter_steps(self):
                return self.loop.iter_steps(training_data)

        Yields:
            int or (int, tuple[np.ndarray]): The step counter, or the step
                counter as well as the step training data.  Will be directly
                given to :meth:`_fit_step` as the `payload` argument.
        """
        raise NotImplementedError()

    def _run_step(self, session, payload):
        """
        Subclasses should override this to run a training step.

        Args:
            session: The TensorFlow session.
            payload: The step payload generated by :meth:`_iter_steps`.
        """
        raise NotImplementedError()

    @property
    def before_epochs(self):
        """
        Get the hooks run before epochs.

        Returns:
            HookList: The hook list.
        """
        return self._before_epochs

    @property
    def after_epochs(self):
        """
        Get the hooks run after epochs.

        Returns:
            HookList: The hook list.
        """
        return self._after_epochs

    @property
    def before_steps(self):
        """
        Get the hooks run before steps.

        Returns:
            HookList: The hook list.
        """
        return self._before_steps

    @property
    def after_steps(self):
        """
        Get the hooks run after steps.

        Returns:
            HookList: The hook list.
        """
        return self._after_steps

    @property
    def hook_lists(self):
        """
        Get all the hook lists.

        Returns:
            tuple[HookList]: The tuple (self.before_epochs, self.before_steps,
                self.after_steps, self.after_epochs).
        """
        return self._hook_lists

    def remove_by_priority(self, priority):
        """
        Remove hooks having the specified `priority` from all lists.

        Args:
            priority: The priority of the hooks to be removed.

        Returns:
            int: The number of removed hooks.
        """
        ret = 0
        for hook_list in self.hook_lists:
            ret += hook_list.remove_by_priority(priority)
        return ret

    def log_after_steps(self, freq):
        """
        Add a logging hook to run after every few steps.

        Args:
            freq (int): The frequency for this logging hook to run.
        """
        self.after_steps.add_hook(
            self.loop.print_logs, freq=freq, priority=HookPriority.LOGGING)

    def log_after_epochs(self, freq):
        """
        Add a logging hook to run after every few epochs.

        Args:
            freq (int): The frequency for this logging hook to run.
        """
        self.after_epochs.add_hook(
            self.loop.print_logs, freq=freq, priority=HookPriority.LOGGING)

    def log_after(self, epochs=None, steps=None):
        """
        Add a logging hook to run after every few epochs or steps.

        Args:
            epochs (None or int): Run validation after every this few `epochs`.
            steps (None or int): Run validation after every this few `steps`.

        Raises:
            ValueError: If both `epochs` and `steps` are specified, or neither
                is specified.
        """
        check_epochs_and_steps_arg(epochs, steps)
        if epochs is not None:
            return self.log_after_epochs(epochs)
        else:
            return self.log_after_steps(steps)

    def remove_log_hooks(self):
        """
        Remove logging hooks from all lists.

        Returns:
            int: The number of removed hooks.
        """
        return self.remove_by_priority(HookPriority.LOGGING)

    def evaluate_after_steps(self, evaluator, freq):
        """
        Add an evaluation hook to run after every few steps.

        Args:
            evaluator (Evaluator or () -> any): A evaluator object
                (which has ``.run()``), or any callable object.
            freq (int): The frequency for this evaluation hook to run.
        """
        callback = evaluator if callable(evaluator) else evaluator.run
        self.after_steps.add_hook(
            callback, freq=freq, priority=HookPriority.EVALUATION)

    def evaluate_after_epochs(self, evaluator, freq):
        """
        Add an evaluation hook to run after every few epochs.

        Args:
            evaluator (Evaluator or () -> any): A evaluator object
                (which has ``.run()``), or any callable object.
            freq (int): The frequency for this evaluation hook to run.
        """
        callback = evaluator if callable(evaluator) else evaluator.run
        self.after_epochs.add_hook(
            callback, freq=freq, priority=HookPriority.EVALUATION)

    def evaluate_after(self, evaluator, epochs=None, steps=None):
        """
        Add an evaluation hook to run after every few epochs or steps.

        Args:
            evaluator (Evaluator or () -> any): A evaluator object
                (which has ``.run()``), or any callable object.
            epochs (None or int): Run validation after every this few `epochs`.
            steps (None or int): Run validation after every this few `steps`.

        Raises:
            ValueError: If both `epochs` and `steps` are specified, or neither
                is specified.
        """
        check_epochs_and_steps_arg(epochs, steps)
        if epochs is not None:
            return self.evaluate_after_epochs(evaluator, freq=epochs)
        else:
            return self.evaluate_after_steps(evaluator, freq=steps)

    def remove_evaluation_hooks(self):
        """
        Remove evaluation hooks from all lists.

        Returns:
            int: The number of removed hooks.
        """
        return self.remove_by_priority(HookPriority.EVALUATION)

    # legacy names for evaluation
    validate_after_steps = evaluate_after_steps
    validate_after_epochs = evaluate_after_epochs
    validate_after = evaluate_after
    remove_validation_hooks = remove_evaluation_hooks

    def anneal_after_steps(self, value, freq):
        """
        Add an annealing hook to run after every few steps.

        Args:
            value (AnnealingDynamicValue or () -> any): An annealing dynamic
                value (which has ``.anneal()``), or any callable object.
            freq (int): The frequency for this annealing hook to run.
        """
        callback = value if callable(value) else value.anneal
        self.after_steps.add_hook(
            callback, freq=freq, priority=HookPriority.ANNEALING)

    def anneal_after_epochs(self, value, freq):
        """
        Add an annealing hook to run after every few epochs.

        Args:
            value (AnnealingDynamicValue or () -> any): An annealing dynamic
                value (which has ``.anneal()``), or any callable object.
            freq (int): The frequency for this annealing hook to run.
        """
        callback = value if callable(value) else value.anneal
        self.after_epochs.add_hook(
            callback, freq=freq, priority=HookPriority.ANNEALING)

    def anneal_after(self, value, epochs=None, steps=None):
        """
        Add an annealing hook to run after every few epochs or steps.

        Args:
            value (AnnealingDynamicValue or () -> any): An annealing dynamic
                value (which has ``.anneal()``), or any callable object.
            epochs (None or int): Run validation after every this few `epochs`.
            steps (None or int): Run validation after every this few `steps`.

        Raises:
            ValueError: If both `epochs` and `steps` are specified, or neither
                is specified.
        """
        check_epochs_and_steps_arg(epochs, steps)
        if epochs is not None:
            return self.anneal_after_epochs(value, freq=epochs)
        else:
            return self.anneal_after_steps(value, freq=steps)

    def remove_annealing_hooks(self):
        """
        Remove annealing hooks from all lists.

        Returns:
            int: The number of removed hooks.
        """
        return self.remove_by_priority(HookPriority.ANNEALING)
