# -*- coding: utf-8 -*-
import tensorflow as tf

__all__ = ['Distribution']


class Distribution(object):
    """
    Base class for probability distributions.

    We heavily rely on `ZhuSuan`_ for its Variational Inference and sampling
    algorithms.  However, its :class:`zhusuan.distributions.Distribution`
    interface does not fits :class:`~tfsnippet.modules.Module` concept well.
    So we maintain our own :class:`Distribution` interface, with thin wrappers
    over those provided by :py:mod:`zhusuan.distributions`.

    A :class:`Distribution` object receives inputs as distribution parameters,
    generating samples and computing probabilities according to these inputs.
    The shape of the inputs can have more dimensions than the nature shape
    of the distribution parameters, since :class:`Distribution` is designed
    to work with batch parameters, samples and probabilities.

    The shape of the parameters of a :class:`Distribution` object would be
    decomposed into ``batch_shape + param_shape``, with `param_shape` being
    the nature shape of the parameter.  For example, a 5-class
    :class:`Categorical` distribution with class probabilities of shape
    ``(3, 4, 5)`` would have ``(3, 4)`` as the `batch_shape`, with ``(5,)``
    as the `param_shape`, corresponding to the probabilities of 5 classes.

    Generating `n` samples from a :class:`Distribution` object would result
    in tensors with shape ``[n] (sample_shape) + batch_shape + value_shape``,
    with ``value_shape`` being the nature shape of an individual sample from
    the distribution.  For example, the `value_shape` of a :class:`Categorical`
    is ``()``, such that the sample shape would be ``(3, 4)``, provided the
    shape of class probabilities is ``(3, 4, 5)``.

    Computing the probabilities (i.e., `prob(x)` or `log_prob(x)`) of samples
    involves broadcasting these samples against the distribution parameters.
    These samples should be broadcastable against ``batch_shape + value_shape``.
    Suppose the shape of the samples can be decomposed into
    ``sample_shape + batch_shape + value_shape``, then by default, the shape of
    the probabilities should be ``sample_shape + batch_shape``, i.e., each
    individual sample resulting in an individual probability value.

    .. _`ZhuSuan`: https://github.com/thu-ml/zhusuan
    """

    @property
    def dtype(self):
        """
        Get the data type of samples.

        Returns:
            tf.DType: Data type of the samples.
        """
        raise NotImplementedError()

    @property
    def is_continuous(self):
        """
        Whether or not the distribution is continuous?

        Returns:
            bool: A boolean indicating whether it is continuous.
        """
        raise NotImplementedError()

    @property
    def is_reparameterized(self):
        """
        Whether or not the distribution is re-parameterized?

        The re-parameterization trick is proposed in [VAE]_, allowing the
        gradients to be propagated back along the samples.
        Note that the re-parameterization can be disabled by specifying
        ``is_reparameterized = False`` as argument of :meth:`sample`.

        Returns:
            bool: A boolean indicating whether it is re-parameterized.
        """
        raise NotImplementedError()

    @property
    def value_shape(self):
        """
        Get the value shape of an individual sample.

        Returns:
            tf.Tensor: The value shape as tensor.
        """
        raise NotImplementedError()

    def get_value_shape(self):
        """
        Get the static value shape of an individual sample.

        Returns:
            tf.TensorShape: The static value shape.
        """
        raise NotImplementedError()

    @property
    def batch_shape(self):
        """
        Get the batch shape of the samples.

        Returns:
            tf.Tensor: The batch shape as tensor.
        """
        raise NotImplementedError()

    def get_batch_shape(self):
        """
        Get the static batch shape of the samples.

        Returns:
            tf.TensorShape: The batch shape.
        """
        raise NotImplementedError()

    def sample(self, n_samples=None, group_ndims=0, is_reparameterized=None,
               name=None):
        """
        Generate samples from the distribution.

        Args:
            n_samples (int or tf.Tensor or None):
                A 0-D `int32` Tensor or None.  How many independent samples
                to draw from the distribution.  The samples will have shape
                ``[n_samples] + batch_shape + value_shape``, or
                ``batch_shape + value_shape`` if `n_samples` is :obj:`None`.

            group_ndims (int or tf.Tensor):
                Number of dimensions at the end of ``[n_samples] + batch_shape``
                to be considered as events group.  This will effect the behavior
                of :meth:`log_prob` and :meth:`prob`. (default 0)

            is_reparameterized (bool):
                If :obj:`True`, raise :class:`RuntimeError` if the distribution
                is not re-parameterized.
                If :obj:`False`, disable re-parameterization even if the
                distribution is re-parameterized.
                (default :obj:`None`, following the setting of distribution)

            name (str):
                TensorFlow name scope of the graph nodes.
                (default "sample").

        Returns:
            tfsnippet.stochastic.StochasticTensor:
                The samples as :class:`~tfsnippet.stochastic.StochasticTensor`.
        """
        raise NotImplementedError()

    def log_prob(self, given, group_ndims=0, name=None):
        """
        Compute the log probability densities of `x` against the distribution.

        Args:
            given (tf.Tensor): The samples to be tested.
            group_ndims (int or tf.Tensor):
                If specified, the last `group_ndims` dimensions of the
                log probability densities will be summed up. (default 0)
            name (str):
                TensorFlow name scope of the graph nodes.
                (default "log_prob").

        Returns:
            tf.Tensor: The log probability densities of `given`.
        """
        raise NotImplementedError()

    def prob(self, given, group_ndims=0, name=None):
        """
        Compute the probability densities of `x` against the distribution.

        Args:
            given (tf.Tensor): The samples to be tested.
            group_ndims (int or tf.Tensor):
                If specified, the last `group_ndims` dimensions of the
                log probability densities will be summed up. (default 0)
            name (str):
                TensorFlow name scope of the graph nodes.
                (default "prob").

        Returns:
            tf.Tensor: The probability densities of `given`.
        """
        raise NotImplementedError()

    @classmethod
    def factory(cls, **kwargs):
        """
        Get a factory for constructing a distribution instance of `cls`,
        with some default parameters.

        .. code-block:: python

            factory = Normal.factory(std=1.)

            # equivalent to Normal(mean=0., std=1.)
            normal = factory(mean=0.)

            # override `std`
            normal = factory(mean=1., std=2.)

            # parameters can also be specified via a dict
            normal = factory({'mean': 0.})

        Args:
            \**kwargs: The default named arguments.

        Returns:
            tfsnippet.distributions.DistributionFactory:
                The distribution factory instance.
        """
        from tfsnippet.distributions import DistributionFactory
        return DistributionFactory(cls, kwargs)
