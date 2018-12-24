import functools

import tensorflow as tf

from .doc_utils import add_name_arg_doc
from .type_utils import is_tensor_object

__all__ = [
    'int_shape', 'resolve_negative_axis',
    'flatten', 'unflatten',
    'get_batch_size', 'get_rank', 'get_shape', 'get_dimensions_size',
    'concat_shapes',
]


def int_shape(tensor):
    """
    Get the int shape tuple of specified `tensor`.

    Args:
        tensor: The tensor object.

    Returns:
        tuple[int or None] or None: The int shape tuple, or :obj:`None`
            if the tensor shape is :obj:`None`.
    """
    tensor = tf.convert_to_tensor(tensor)
    shape = tensor.get_shape()
    if shape.ndims is None:
        shape = None
    else:
        shape = tuple((int(v) if v is not None else None)
                      for v in shape.as_list())
    return shape


def resolve_negative_axis(ndims, axis):
    """
    Resolve all negative `axis` indices according to `ndims` into positive.

    Usage::

        resolve_negative_axis(4, [0, -1, -2])  # output: (0, 3, 2)

    Args:
        ndims (int): Number of total dimensions.
        axis (Iterable[int]): The axis indices.

    Returns:
        tuple[int]: The resolved positive axis indices.

    Raises:
        ValueError: If any index in `axis` is out of range.
    """
    axis = tuple(int(a) for a in axis)
    ret = []
    for a in axis:
        if a < 0:
            a += ndims
        if a < 0 or a >= ndims:
            raise ValueError('`axis` out of range: {} vs ndims {}.'.
                             format(axis, ndims))
        ret.append(a)
    return tuple(ret)


@add_name_arg_doc
def flatten(x, k, name=None):
    """
    Flatten the front dimensions of `x`, such that the resulting tensor
    will have at most `k` dimensions.

    Args:
        x (Tensor): The tensor to be flatten.
        k (int): The maximum number of dimensions for the resulting tensor.

    Returns:
        (tf.Tensor, tuple[int or None], tuple[int] or tf.Tensor) or (tf.Tensor, None, None):
            (The flatten tensor, the static front shape, and the front shape),
            or (the original tensor, None, None)
    """
    x = tf.convert_to_tensor(x)
    if k < 1:
        raise ValueError('`k` must be greater or equal to 1.')
    if not x.get_shape():
        raise ValueError('`x` is required to have known number of '
                         'dimensions.')
    shape = int_shape(x)
    if len(shape) < k:
        raise ValueError('`k` is {}, but `x` only has rank {}.'.
                         format(k, len(shape)))
    if len(shape) == k:
        return x, None, None

    with tf.name_scope(name, default_name='flatten', values=[x]):
        if k == 1:
            static_shape = shape
            if None in shape:
                shape = tf.shape(x)
            return tf.reshape(x, [-1]), static_shape, shape
        else:
            front_shape, back_shape = shape[:-(k-1)], shape[-(k-1):]
            static_front_shape = front_shape
            static_back_shape = back_shape
            if None in front_shape or None in back_shape:
                dynamic_shape = tf.shape(x)
                if None in front_shape:
                    front_shape = dynamic_shape[:-(k-1)]
                if None in back_shape:
                    back_shape = dynamic_shape[-(k-1):]
            if isinstance(back_shape, tuple):
                x = tf.reshape(x, [-1] + list(back_shape))
            else:
                x = tf.reshape(x, tf.concat([[-1], back_shape], axis=0))
                x.set_shape(tf.TensorShape([None] + list(static_back_shape)))
            return x, static_front_shape, front_shape


@add_name_arg_doc
def unflatten(x, static_front_shape, front_shape, name=None):
    """
    The inverse transformation of :func:`flatten`.

    If both `static_front_shape` is None and `front_shape` is None,
    `x` will be returned without any change.

    Args:
        x (Tensor): The tensor to be unflatten.
        static_front_shape (tuple[int or None] or None): The static front shape.
        front_shape (tuple[int] or tf.Tensor or None): The front shape.

    Returns:
        tf.Tensor: The unflatten x.
    """
    x = tf.convert_to_tensor(x)
    if static_front_shape is None and front_shape is None:
        return x
    if not x.get_shape():
        raise ValueError('`x` is required to have known number of '
                         'dimensions.')
    shape = int_shape(x)
    if len(shape) < 1:
        raise ValueError('`x` only has rank {}, required at least 1.'.
                         format(len(shape)))
    if not is_tensor_object(front_shape):
        front_shape = tuple(front_shape)

    with tf.name_scope(name, default_name='unflatten', values=[x]):
        back_shape = shape[1:]
        static_back_shape = back_shape
        if None in back_shape:
            back_shape = tf.shape(x)[1:]
        if isinstance(front_shape, tuple) and isinstance(back_shape, tuple):
            x = tf.reshape(x, front_shape + back_shape)
        else:
            x = tf.reshape(x, tf.concat([front_shape, back_shape], axis=0))
            x.set_shape(tf.TensorShape(list(static_front_shape) +
                                       list(static_back_shape)))
        return x


@add_name_arg_doc
def get_batch_size(tensor, axis=0, name=None):
    """
    Infer the mini-batch size according to `tensor`.

    Args:
        tensor (tf.Tensor): The input placeholder.
        axis (int): The axis of mini-batches.  Default is 0.

    Returns:
        int or tf.Tensor: The batch size.
    """
    tensor = tf.convert_to_tensor(tensor)
    axis = int(axis)
    with tf.name_scope(name, default_name='get_batch_size', values=[tensor]):
        batch_size = None
        shape = int_shape(tensor)
        if shape is not None:
            batch_size = shape[axis]
        if batch_size is None:
            batch_size = tf.shape(tensor)[axis]
    return batch_size


def get_rank(tensor, name=None):
    """
    Get the rank of the tensor.

    Args:
        tensor (tf.Tensor): The tensor to be tested.
        name: TensorFlow name scope of the graph nodes.

    Returns:
        int or tf.Tensor: The rank.
    """
    tensor = tf.convert_to_tensor(tensor)
    tensor_shape = int_shape(tensor)
    if tensor_shape is not None:
        return len(tensor_shape)
    return tf.rank(tensor, name=name)


@add_name_arg_doc
def get_dimensions_size(tensor, axis=None, name=None):
    """
    Get the size of `tensor` of specified `axis`.

    If `axis` is :obj:`None`, select the size of all dimensions.

    Args:
        tensor (tf.Tensor): The tensor to be tested.
        axis (Iterable[int] or None): The dimensions to be selected.

    Returns:
        tuple[int] or tf.Tensor: A tuple of integers if all selected
            dimensions have static sizes.  Otherwise a tensor.
    """
    tensor = tf.convert_to_tensor(tensor)
    if axis is not None:
        axis = tuple(axis)
        if not axis:
            return ()

    with tf.name_scope(name, default_name='get_dimensions_size',
                       values=[tensor]):
        shape = int_shape(tensor)

        if shape is not None and axis is not None:
            shape = tuple(shape[a] for a in axis)

        if shape is None or None in shape:
            dynamic_shape = tf.shape(tensor)
            if axis is None:
                shape = dynamic_shape
            else:
                shape = tf.stack([dynamic_shape[i] for i in axis], axis=0)

        return shape


get_shape = functools.partial(get_dimensions_size, axis=None)


@add_name_arg_doc
def concat_shapes(shapes, name=None):
    """
    Concat shapes from `shapes`.

    Args:
        shapes (Iterable[tuple[int] or tf.Tensor]): List of shape tuples
            or tensors.

    Returns:
        tuple[int] or tf.Tensor: The concatenated shape.
    """
    shapes = tuple(shapes)
    if any(is_tensor_object(s) for s in shapes):
        shapes = [
            s if is_tensor_object(s) else tf.constant(s, dtype=tf.int32)
            for s in shapes
        ]
        with tf.name_scope(name, default_name='concat_shapes', values=shapes):
            return tf.concat(shapes, axis=0)
    else:
        return sum((tuple(s) for s in shapes), ())
